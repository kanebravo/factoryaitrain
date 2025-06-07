import re
import subprocess
import tempfile
import os
import logging
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAIAgent

from .base_agent import AgentBase
from ..models.proposal_models import (
    UnderstandingRequirements,
    SolutionOverview,
    SolutionArchitecture,
    OEMSolutionReview
)
from ..utils.exceptions import LLMGenerationError, MermaidValidationError, ConfigurationError
from ..utils.config_loader import load_prompts

logger = logging.getLogger(__name__)

class UnderstandingRequirementsOutput(BaseModel):
    understanding_requirements_content: str = Field(description="Narrative understanding of client requirements, derived from RFP analysis.")

class SolutionOverviewOutput(BaseModel):
    solution_overview_content: str = Field(description="Detailed overview of the proposed solution.")

class SolutionArchitectureTextOutput(BaseModel):
    solution_architecture_descriptive_text: str = Field(description="Textual description of the solution architecture.")

class SolutionArchitectureMermaidOutput(BaseModel):
    solution_architecture_mermaid_script: str = Field(description="Mermaid script for the solution architecture diagram. Should be enclosed in ```mermaid ... ```.")

class TechnicalContentSet(BaseModel):
    understanding_requirements_content: str = Field(description="Narrative understanding of client requirements, derived from RFP analysis.")
    solution_overview_content: str = Field(description="Detailed overview of the proposed solution.")
    solution_architecture_descriptive_text: str = Field(description="Textual description of the solution architecture.")
    solution_architecture_mermaid_script: str = Field(description="Mermaid script for the solution architecture diagram. Should be enclosed in ```mermaid ... ```.")
    mermaid_validation_error: Optional[str] = Field(None, description="Error message if Mermaid script validation failed.")

class TechnicalWriterAgent(AgentBase):
    DEFAULT_PROMPTS = {
        "understanding_requirements": """You are a senior technical writer. Based on the provided Request for Proposal (RFP) details, generate a narrative that demonstrates a clear understanding of the client's needs and objectives.

**Chosen Primary Technology (for context, but don't focus on solutioning yet):** {chosen_technology}

**RFP Details:**
*   RFP Full Text (truncated): {truncated_rfp_text}
*   RFP Summary: {summary_str}
*   Key Client Requirements:
    {requirements_str}

**Output Requirement:**
Write a narrative that demonstrates a clear understanding of the client's needs and objectives as expressed in the RFP. Synthesize information from the RFP summary, key requirements, and overall text. This should not just be a list but a thoughtful interpretation.
Return ONLY the narrative text.""",
        "solution_overview": """You are a senior technical writer and solution architect.
Based on the client's requirements (summarized below) and the chosen primary technology, provide a detailed overview of the proposed solution.

**Chosen Primary Technology:** {chosen_technology}

**Understanding of Client's Requirements:**
{understanding_content}

**RFP Details (for context):**
*   RFP Summary: {summary_str}
*   Key Client Requirements:
    {requirements_str}

**Output Requirement:**
Provide a detailed overview of the proposed solution. Explain how it addresses the client's main problems/objectives using the "{chosen_technology}".
Describe the core components, functionalities, and benefits of your proposed solution.
Return ONLY the solution overview text.""",
        "solution_architecture_text": """You are a senior solution architect. Based on the provided solution overview and chosen technology, describe the proposed solution architecture.

**Chosen Primary Technology:** {chosen_technology}

**Solution Overview:**
{solution_overview_content}

**Key Client Requirements (for context):**
{requirements_str}

**Output Requirement:**
Describe the proposed solution architecture. Detail the main components, layers, interactions, and data flows.
Explain how the "{chosen_technology}" fits into this architecture.
Return ONLY the descriptive text for the solution architecture.""",
        "solution_architecture_mermaid": """You are a solution architect. Based on the provided solution architecture description and chosen technology, generate a Mermaid diagram script.

**Solution Architecture Description:**
{solution_architecture_text}

**Chosen Primary Technology (for context in diagram labels if appropriate):** {chosen_technology}

**Output Requirement:**
Generate a Mermaid diagram script (enclosed in ```mermaid ... ```) representing the conceptual or reference architecture described.
The diagram should be clear, concise, and accurately reflect the textual description. For example:
```mermaid
graph TD;
    UserInterface --> API_Gateway;
    API_Gateway --> Microservice1;
    API_Gateway --> Microservice2;
    Microservice1 --> Database;
    Microservice2 --> Database;
    Microservice2 --> ExternalService;
```
Ensure the Mermaid syntax is correct. Use common diagram types like `graph TD`, `sequenceDiagram`, or `classDiagram` as appropriate.
Return ONLY the Mermaid script, including the ```mermaid ... ``` fences.""",
        "oem_review": """You are a technical writer. Please generate an overview of the OEM product: "{oem_product_name}".
This overview will be part of a larger project proposal.
Describe what the product is, its main features, and its general benefits.
If context from an RFP is provided below, briefly mention how this product might be relevant.

{summary_str}
{requirements_str}

Structure your response to fit the fields of the OEMSolutionReview model: 'oem_product_name' (which is "{oem_product_name}"), 'title', and 'content'.
The 'title' should be something like "Overview: {oem_product_name}".
The 'content' should be the detailed overview."""
    }

    def __init__(self, model_name: str = "openai:gpt-3.5-turbo"):
        super().__init__(model_name=model_name)
        self.llm_agent = PydanticAIAgent(model=self.model_name)
        self.mmdc_path = self._find_mmdc_path()
        if not self.mmdc_path:
            logger.warning("TWAgent: mmdc (Mermaid CLI) not found in PATH. Mermaid diagram validation will be limited.")

        try:
            loaded_prompts = load_prompts()
        except ConfigurationError as e:
            logger.warning(f"TWAgent: Failed to load prompts from JSON file ({e}). Using default prompts for all operations.")
            loaded_prompts = {}
        except Exception as e:
            logger.error(f"TWAgent: An unexpected error occurred loading prompts: {e}. Using default prompts.")
            loaded_prompts = {}

        prompt_keys = [
            "understanding_requirements", "solution_overview",
            "solution_architecture_text", "solution_architecture_mermaid", "oem_review"
        ]
        for key in prompt_keys:
            default_prompt = self.DEFAULT_PROMPTS[key]
            loaded_prompt = loaded_prompts.get(key)

            setattr(self, f"{key}_prompt", default_prompt)
            if loaded_prompt is None:
                logger.warning(f"TWAgent: Prompt '{key}' not loaded. Using default.")
            elif loaded_prompt == default_prompt:
                 logger.info(f"TWAgent: Prompt '{key}' is identical to default.")
            else:
                logger.info(f"TWAgent: Custom prompt for '{key}' loaded.")
                setattr(self, f"{key}_prompt", loaded_prompt)

    def _find_mmdc_path(self) -> Optional[str]:
        try:
            process = subprocess.run(["mmdc", "--version"], capture_output=True, text=True, check=True)
            if process.returncode == 0:
                return "mmdc"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        return None

    def _validate_mermaid_basic(self, script: str) -> bool:
        if not script or not isinstance(script, str):
            logger.warning("TWAgent: Basic Mermaid Validation: Script is empty or not a string.")
            return False
        clean_script_for_basic_check = script.strip()
        if not (clean_script_for_basic_check.startswith("```mermaid") and clean_script_for_basic_check.endswith("```")):
            logger.warning("TWAgent: Basic Mermaid Validation: Script does not start/end with ```mermaid ... ``` fences.")
            if not re.search(r"^\s*(graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|gitGraph)", clean_script_for_basic_check, re.MULTILINE):
                 return False
        if not re.search(r"(graph\s+(TD|LR|BT|RL)|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|gitGraph)", clean_script_for_basic_check):
            logger.warning("TWAgent: Basic Mermaid Validation: No common graph definition found.")
            return False
        brackets = {"(": ")", "[": "]", "{": "}"}
        stack = []
        for char in clean_script_for_basic_check:
            if char in brackets.keys():
                stack.append(char)
            elif char in brackets.values():
                if not stack or brackets[stack.pop()] != char:
                    logger.warning(f"TWAgent: Basic Mermaid Validation: Potentially mismatched bracket '{char}'.")
                    pass
        logger.info("TWAgent: Basic Mermaid validation passed.")
        return True

    async def _validate_mermaid_with_cli(self, script: str) -> tuple[bool, str]:
        if not self.mmdc_path:
            message = "mmdc (Mermaid CLI) not found. Skipping CLI validation."
            logger.warning(f"TWAgent: {message}")
            return True, message
        clean_script = script.strip()
        if clean_script.startswith("```mermaid") and clean_script.endswith("```"):
            clean_script = clean_script[len("```mermaid"):-len("```")].strip()
        elif clean_script.startswith("mermaid"):
             clean_script = clean_script[len("mermaid"):].strip()
        if not clean_script:
            message = "Mermaid script is empty after removing fences."
            logger.warning(f"TWAgent: CLI Mermaid Validation: {message}")
            return False, message
        temp_mmd_file = None
        temp_svg_file = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".mmd") as tmp_in:
                tmp_in.write(clean_script)
                temp_mmd_file = tmp_in.name
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".svg") as tmp_out:
                temp_svg_file = tmp_out.name
            command = [self.mmdc_path, "-i", temp_mmd_file, "-o", temp_svg_file, "-w", "1024"]
            process = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if process.returncode == 0:
                message = "Mermaid script validated successfully with mmdc."
                logger.info(f"TWAgent: CLI Mermaid Validation: {message}")
                return True, message
            else:
                error_output = process.stderr or process.stdout
                message = f"Mermaid script validation failed with mmdc. Return code: {process.returncode}. Error: {error_output.strip()}"
                logger.warning(f"TWAgent: CLI Mermaid Validation: {message}")
                return False, message
        except FileNotFoundError:
            message = "mmdc command not found during execution."
            logger.error(f"TWAgent: CLI Mermaid Validation: {message}")
            self.mmdc_path = None
            return True, message
        except subprocess.TimeoutExpired:
            message = "Mermaid script validation with mmdc timed out."
            logger.warning(f"TWAgent: CLI Mermaid Validation: {message}")
            return False, message
        except Exception as e:
            message = f"An unexpected error occurred during mmdc validation: {e}"
            logger.error(f"TWAgent: CLI Mermaid Validation: {message}")
            return False, message
        finally:
            if temp_mmd_file and os.path.exists(temp_mmd_file):
                os.remove(temp_mmd_file)
            if temp_svg_file and os.path.exists(temp_svg_file):
                os.remove(temp_svg_file)

    async def _generate_understanding_requirements(
        self, rfp_full_text: str, rfp_summary: Optional[str],
        key_requirements: List[str], chosen_technology: str
    ) -> str:
        requirements_str = "- " + "\n- ".join(key_requirements) if key_requirements else "Not explicitly listed."
        summary_str = rfp_summary if rfp_summary else "No summary provided."
        max_rfp_text_len = 4000
        truncated_rfp_text = rfp_full_text[:max_rfp_text_len]
        if len(rfp_full_text) > max_rfp_text_len:
            truncated_rfp_text += "\n... [RFP text truncated for brevity]"

        final_prompt = self.understanding_requirements_prompt.format(
            chosen_technology=chosen_technology,
            truncated_rfp_text=truncated_rfp_text,
            summary_str=summary_str,
            requirements_str=requirements_str
        )
        try:
            run_result_container = await self.llm_agent.run(
                output_type=UnderstandingRequirementsOutput, user_prompt=final_prompt
            )
            if run_result_container and hasattr(run_result_container, 'output') and \
               run_result_container.output and run_result_container.output.understanding_requirements_content:
                return run_result_container.output.understanding_requirements_content
            else:
                err_msg = "LLM did not return expected output or content was empty for understanding requirements."
                logger.error(f"TWAgent: {err_msg} - Container: {run_result_container}")
                raise LLMGenerationError(message=err_msg, agent_name="TechnicalWriterAgent")
        except Exception as e:
            logger.error(f"TWAgent: LLM call failed for understanding requirements: {e.__class__.__name__}: {e}")
            raise LLMGenerationError(
                message=f"Failed to generate understanding of requirements: {e}",
                agent_name="TechnicalWriterAgent"
            ) from e

    async def _generate_solution_overview(
        self, rfp_summary: Optional[str], key_requirements: List[str],
        chosen_technology: str, understanding_content: str
    ) -> str:
        requirements_str = "- " + "\n- ".join(key_requirements) if key_requirements else "Not explicitly listed."
        summary_str = rfp_summary if rfp_summary else "No summary provided."
        final_prompt = self.solution_overview_prompt.format(
            chosen_technology=chosen_technology,
            understanding_content=understanding_content,
            summary_str=summary_str,
            requirements_str=requirements_str
        )
        try:
            run_result_container = await self.llm_agent.run(
                output_type=SolutionOverviewOutput, user_prompt=final_prompt
            )
            if run_result_container and hasattr(run_result_container, 'output') and \
               run_result_container.output and run_result_container.output.solution_overview_content:
                return run_result_container.output.solution_overview_content
            else:
                err_msg = "LLM did not return expected output or content was empty for solution overview."
                logger.error(f"TWAgent: {err_msg} - Container: {run_result_container}")
                raise LLMGenerationError(message=err_msg, agent_name="TechnicalWriterAgent")
        except Exception as e:
            logger.error(f"TWAgent: LLM call failed for solution overview: {e.__class__.__name__}: {e}")
            raise LLMGenerationError(
                message=f"Failed to generate solution overview: {e}",
                agent_name="TechnicalWriterAgent"
            ) from e

    async def _generate_solution_architecture_text(
        self, chosen_technology: str, solution_overview_content: str, key_requirements: List[str]
    ) -> str:
        requirements_str = "- " + "\n- ".join(key_requirements) if key_requirements else "Not explicitly listed."
        final_prompt = self.solution_architecture_text_prompt.format(
            chosen_technology=chosen_technology,
            solution_overview_content=solution_overview_content,
            requirements_str=requirements_str
        )
        try:
            run_result_container = await self.llm_agent.run(
                output_type=SolutionArchitectureTextOutput, user_prompt=final_prompt
            )
            if run_result_container and hasattr(run_result_container, 'output') and \
               run_result_container.output and run_result_container.output.solution_architecture_descriptive_text:
                return run_result_container.output.solution_architecture_descriptive_text
            else:
                err_msg = "LLM did not return expected output or content was empty for solution architecture text."
                logger.error(f"TWAgent: {err_msg} - Container: {run_result_container}")
                raise LLMGenerationError(message=err_msg, agent_name="TechnicalWriterAgent")
        except Exception as e:
            logger.error(f"TWAgent: LLM call failed for solution architecture text: {e.__class__.__name__}: {e}")
            raise LLMGenerationError(
                message=f"Failed to generate solution architecture text: {e}",
                agent_name="TechnicalWriterAgent"
            ) from e

    async def _generate_solution_architecture_mermaid(
        self, solution_architecture_text: str, chosen_technology: str
    ) -> tuple[str, Optional[str]]:
        final_prompt = self.solution_architecture_mermaid_prompt.format(
            solution_architecture_text=solution_architecture_text,
            chosen_technology=chosen_technology
        )
        mermaid_script = ""
        validation_err_str: Optional[str] = None
        try:
            run_result_container = await self.llm_agent.run(
                output_type=SolutionArchitectureMermaidOutput, user_prompt=final_prompt
            )
            if not (run_result_container and hasattr(run_result_container, 'output') and \
                    run_result_container.output and run_result_container.output.solution_architecture_mermaid_script):
                err_msg = "LLM did not return expected output or script was empty for Mermaid diagram."
                logger.error(f"TWAgent: {err_msg} - Container: {run_result_container}")
                raise LLMGenerationError(message=err_msg, agent_name="TechnicalWriterAgent")

            mermaid_script = run_result_container.output.solution_architecture_mermaid_script
            if not mermaid_script.strip().startswith("```mermaid"):
                mermaid_script = "```mermaid\n" + mermaid_script.strip()
            if not mermaid_script.strip().endswith("```"):
                mermaid_script = mermaid_script.strip() + "\n```"

            basic_validation_passed = self._validate_mermaid_basic(mermaid_script)
            if not basic_validation_passed:
                validation_err_str = "Basic Mermaid syntax validation failed. Script may be malformed."
                logger.warning(f"TWAgent: {validation_err_str} - Script: {mermaid_script[:200]}...")

            cli_valid, cli_message = await self._validate_mermaid_with_cli(mermaid_script)
            if not cli_valid:
                if "mmdc not found" not in cli_message and "timed out" not in cli_message and "unexpected error" not in cli_message:
                    final_validation_err_msg = f"Mermaid CLI validation failed: {cli_message}"
                    logger.warning(f"TWAgent: {final_validation_err_msg} - Script: {mermaid_script[:200]}...")
                    raise MermaidValidationError(message=final_validation_err_msg, agent_name="TechnicalWriterAgent")
                elif "mmdc not found" in cli_message:
                     logger.info(f"TWAgent: Mermaid CLI validation skipped: {cli_message}")
                     if not basic_validation_passed: validation_err_str = (validation_err_str or "") + f" CLI check skipped: {cli_message}"
                elif not basic_validation_passed:
                    raise MermaidValidationError(message=validation_err_str or "Basic Mermaid syntax validation failed and CLI validation could not be performed.", agent_name="TechnicalWriterAgent")

            reportable_error: Optional[str] = None
            if "mmdc not found" in cli_message or "timed out" in cli_message :
                reportable_error = cli_message
            elif validation_err_str and cli_valid:
                reportable_error = validation_err_str

            return mermaid_script, reportable_error
        except LLMGenerationError: raise
        except MermaidValidationError: raise
        except Exception as e:
            logger.error(f"TWAgent: LLM call failed for Mermaid script: {e.__class__.__name__}: {e}")
            raise LLMGenerationError(
                message=f"Failed to generate Mermaid script: {e}",
                agent_name="TechnicalWriterAgent"
            ) from e

    async def generate_all_technical_content(
        self, rfp_full_text: str, rfp_summary: Optional[str],
        key_requirements: List[str], evaluation_criteria: Optional[List[str]],
        chosen_technology: str
    ) -> TechnicalContentSet:
        if not rfp_full_text and not rfp_summary and not key_requirements:
            raise ValueError("Some RFP context (full text, summary, or key requirements) must be provided.")
        if not chosen_technology:
            raise ValueError("A chosen technology must be specified.")

        understanding_content = await self._generate_understanding_requirements(
            rfp_full_text, rfp_summary, key_requirements, chosen_technology
        )
        solution_overview_content = await self._generate_solution_overview(
            rfp_summary, key_requirements, chosen_technology, understanding_content
        )
        solution_architecture_text = await self._generate_solution_architecture_text(
            chosen_technology, solution_overview_content, key_requirements
        )
        mermaid_script, mermaid_reportable_error = await self._generate_solution_architecture_mermaid(
            solution_architecture_text, chosen_technology
        )
        return TechnicalContentSet(
            understanding_requirements_content=understanding_content,
            solution_overview_content=solution_overview_content,
            solution_architecture_descriptive_text=solution_architecture_text,
            solution_architecture_mermaid_script=mermaid_script,
            mermaid_validation_error=mermaid_reportable_error
        )

    async def generate_oem_review(
        self, oem_product_name: str, key_requirements: Optional[List[str]] = None,
        rfp_summary: Optional[str] = None
    ) -> OEMSolutionReview:
        if not oem_product_name:
            raise ValueError("OEM product name must be provided.")

        requirements_str = ("\nKey RFP Requirements for context (if available):\n- " + "\n- ".join(key_requirements)) if key_requirements else ""
        summary_str = f"\nRFP Summary for context (if available): {rfp_summary}" if rfp_summary else ""

        final_prompt = self.oem_review_prompt.format(
            oem_product_name=oem_product_name,
            summary_str=summary_str,
            requirements_str=requirements_str
        )
        try:
            run_result_container = await self.llm_agent.run(
                output_type=OEMSolutionReview, user_prompt=final_prompt
            )
            if run_result_container and hasattr(run_result_container, 'output') and \
               run_result_container.output and run_result_container.output.content:
                review_output: OEMSolutionReview = run_result_container.output
                review_output.oem_product_name = oem_product_name
                if not review_output.title or review_output.title == "OEM Product Overview":
                     review_output.title = f"Overview: {oem_product_name}"
                return review_output
            else:
                err_msg = f"LLM did not return expected output or content was empty for OEM review of '{oem_product_name}'."
                logger.error(f"TWAgent: {err_msg} - Container: {run_result_container}")
                raise LLMGenerationError(message=err_msg, agent_name="TechnicalWriterAgent")
        except Exception as e:
            logger.error(f"TWAgent: LLM call failed for OEM review of '{oem_product_name}': {e.__class__.__name__}: {e}")
            raise LLMGenerationError(
                message=f"Failed to generate OEM review for '{oem_product_name}': {e}",
                agent_name="TechnicalWriterAgent"
            ) from e

if __name__ == '__main__':
    import asyncio
    # from dotenv import load_dotenv # Not needed for direct script test if key is in env

    async def main_test():
        print("Testing TechnicalWriterAgent (Standalone)...")
        # load_dotenv() # Ensure .env is loaded if you run this script directly
        if not os.getenv("OPENAI_API_KEY"):
            print("FATAL: OPENAI_API_KEY not found. Please set it in .env file or environment.")
            return

        sample_rfp_text = "Our company seeks a new CRM system. It must be cloud-based, support sales and marketing, and integrate with our accounting software. We need mobile access and custom reporting. The goal is to improve sales productivity by 20%."
        sample_summary = "Client needs a new cloud-based CRM for sales/marketing with accounting integration, mobile access, and custom reporting to boost sales productivity."
        sample_requirements = ["Cloud-based CRM", "Sales and Marketing modules", "Accounting integration", "Mobile access", "Custom reporting"]
        sample_criteria = ["Ease of use", "Integration capabilities", "Cost"]
        sample_technology_generic = "A Custom Python-based CRM Solution"

        try:
            # Example: Use a specific model if needed for testing
            # agent_generic = TechnicalWriterAgent(model_name="openai:gpt-4-turbo")
            agent_generic = TechnicalWriterAgent() # Uses default gpt-3.5-turbo
            print(f"TechnicalWriterAgent initialized with model: {agent_generic.model_name}")

            print("\n--- Generating Technical Content Set (Generic Tech) ---")
            technical_set_generic = await agent_generic.generate_all_technical_content(
                rfp_full_text=sample_rfp_text,
                rfp_summary=sample_summary,
                key_requirements=sample_requirements,
                evaluation_criteria=sample_criteria,
                chosen_technology=sample_technology_generic
            )
            print(f"Understanding: {technical_set_generic.understanding_requirements_content[:150]}...")
            print(f"Overview: {technical_set_generic.solution_overview_content[:150]}...")
            print(f"Architecture Text: {technical_set_generic.solution_architecture_descriptive_text[:150]}...")
            print(f"Mermaid Script:\n{technical_set_generic.solution_architecture_mermaid_script}")
            if technical_set_generic.mermaid_validation_error:
                print(f"Mermaid Validation Info: {technical_set_generic.mermaid_validation_error}")


            oem_product = "Salesforce Sales Cloud"
            print(f"\n--- Generating OEM Review for: {oem_product} ---")
            oem_review = await agent_generic.generate_oem_review(
                oem_product_name=oem_product,
                key_requirements=sample_requirements,
                rfp_summary=sample_summary
            )
            print(f"OEM Review Title: {oem_review.title}")
            print(f"OEM Review Content: {oem_review.content[:200]}...")

        except (LLMGenerationError, MermaidValidationError, ConfigurationError) as custom_error:
            print(f"A known application error occurred: {custom_error}")
        except ValueError as ve: # Catch specific ValueErrors from input validation
            print(f"Input Error: {ve}")
        except Exception as e: # Catch any other unexpected errors
            import traceback
            print(f"An unexpected error occurred: {e.__class__.__name__} - {e}")
            print(traceback.format_exc())

    if __name__ == '__main__':
        asyncio.run(main_test())
