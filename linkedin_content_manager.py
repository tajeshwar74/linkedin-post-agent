#!/usr/bin/env python3
"""Research, write, review, optimize, and prepare LinkedIn content with CrewAI."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv


# Load local configuration before constructing any provider or tool clients.
load_dotenv()

LOGGER = logging.getLogger("linkedin_content_manager")
STAGE_SEPARATOR = "=" * 78


class ConfigurationError(Exception):
    """Raised when a required local configuration value is missing."""


def configure_api_keys() -> str:
    """Validate required keys and expose the AI Studio key to provider SDKs."""
    ai_studio_api_key = os.getenv("AI_STUDIO_API_KEY", "").strip()
    serper_api_key = os.getenv("SERPER_API_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("AI_STUDIO_API_KEY", ai_studio_api_key),
            ("SERPER_API_KEY", serper_api_key),
        )
        if not value
    ]
    if missing:
        raise ConfigurationError(
            "Missing required environment variable(s): "
            f"{', '.join(missing)}. Add them to your .env file; see .env.example."
        )

    # CrewAI's Google-backed memory provider reads this variable.
    os.environ["GOOGLE_API_KEY"] = ai_studio_api_key
    return ai_studio_api_key


def make_stage_callback(
    stage_name: str,
    on_complete: Callable[[str, Any], None] | None = None,
) -> Callable[[Any], None]:
    """Print and optionally forward a task result when its stage finishes."""

    def print_stage_output(task_output: Any) -> None:
        print(f"\n{STAGE_SEPARATOR}\n{stage_name.upper()}\n{STAGE_SEPARATOR}")
        print(task_output.raw)
        if on_complete is not None:
            on_complete(stage_name, task_output)

    return print_stage_output


def build_crew(
    ai_studio_api_key: str,
    on_stage_complete: Callable[[str, Any], None] | None = None,
) -> Any:
    """Create the five-agent, five-task sequential publishing workflow."""
    try:
        from crewai import Agent, Crew, LLM, Process, Task
        from crewai_tools import SerperDevTool
    except ImportError as exc:
        raise RuntimeError(
            "CrewAI dependencies are not installed. Run "
            "'python -m pip install -r requirements.txt'."
        ) from exc

    # Use the Flash-Lite model currently accepted by this AI Studio account.
    llm = LLM(
        model="gemini/gemini-3.5-flash-lite",
        api_key=ai_studio_api_key,
        temperature=0.7,
    )
    web_search = SerperDevTool()

    # Agent 1: find timely, credible material that can support a LinkedIn post.
    trend_researcher = Agent(
        role="Trend Researcher Agent",
        goal=(
            "Find current, relevant developments and trustworthy evidence for "
            "the user's LinkedIn topic, then identify useful audience insights."
        ),
        backstory=(
            "You are a meticulous industry researcher. You verify recency, "
            "distinguish facts from opinion, and provide source names, links, "
            "dates, and caveats instead of inventing evidence."
        ),
        tools=[web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # Agent 2: turn verified research into a specific, readable first draft.
    content_writer = Agent(
        role="Content Writer Agent",
        goal=(
            "Draft an original LinkedIn post for the given topic and audience, "
            "grounded in the research and written in a human, credible voice."
        ),
        backstory=(
            "You are an experienced LinkedIn writer who favors a strong opening, "
            "clear takeaways, concise paragraphs, and a natural conversation "
            "starter over hype, jargon, or engagement bait."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # Agent 3: give actionable editorial feedback without rewriting the post.
    content_critic = Agent(
        role="Content Critic Agent",
        goal=(
            "Evaluate the draft for factual support, clarity, relevance, "
            "originality, tone, structure, and LinkedIn readability."
        ),
        backstory=(
            "You are a rigorous but constructive editor. You flag unsupported "
            "claims and clichés, explain the impact of each issue, and give "
            "prioritized, concrete recommendations."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # Agent 4: apply the critique and produce the best publish-ready version.
    content_optimizer = Agent(
        role="Content Optimizer Agent",
        goal=(
            "Resolve the critic's highest-value issues and deliver one polished, "
            "publish-ready LinkedIn post without adding unsupported claims."
        ),
        backstory=(
            "You are a precise copy editor focused on readability, a strong "
            "opening, useful insight, and an authentic call to conversation. "
            "You preserve the writer's intent and avoid keyword stuffing."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # Agent 5: recommend when and how to publish; do not claim to post or schedule.
    scheduling_agent = Agent(
        role="Scheduling Agent",
        goal=(
            "Prepare practical LinkedIn publication recommendations for the "
            "optimized post, including timing, timezone assumptions, and a "
            "pre-publication checklist."
        ),
        backstory=(
            "You are a social publishing strategist. You offer testable timing "
            "recommendations rather than guarantees, tailor advice to the "
            "audience when details are available, and clearly state assumptions."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # CrewAI's sequential process passes earlier task output as task context.
    # Explicit context lists make that dependency unambiguous for every stage.
    research_task = Task(
        description=(
            "Research the topic/niche: {topic}. Find recent developments, "
            "reliable facts or data, audience-relevant implications, and useful "
            "source links. Prefer primary or reputable sources, note publication "
            "dates, and distinguish verified facts from interpretation. Do not "
            "draft the LinkedIn post yet."
        ),
        expected_output=(
            "A concise research brief with 3-5 evidence-backed findings, source "
            "names and URLs, publication dates when available, audience insights, "
            "and any important uncertainty or caveat."
        ),
        agent=trend_researcher,
        callback=make_stage_callback("Research", on_stage_complete),
    )
    writing_task = Task(
        description=(
            "Using the research brief and the topic/niche ({topic}), write one "
            "original LinkedIn post for a professional audience. Lead with a "
            "specific hook, develop one clear central point, use short readable "
            "paragraphs, and end with a relevant question or invitation. Use "
            "only claims supported by the research. Do not include fabricated "
            "personal experience or citations that were not found."
        ),
        expected_output=(
            "One complete first-draft LinkedIn post, followed by a short note "
            "identifying its intended audience and central takeaway."
        ),
        agent=content_writer,
        context=[research_task],
        callback=make_stage_callback("Writing", on_stage_complete),
    )
    critique_task = Task(
        description=(
            "Review the draft against the research brief. Assess factual "
            "accuracy, hook, clarity, originality, audience fit, tone, "
            "readability, and call to conversation. Identify unsupported or "
            "overstated claims and prioritize specific edits. Do not produce a "
            "replacement post."
        ),
        expected_output=(
            "A prioritized editorial review with strengths, issues tied to "
            "specific draft content, factual risks, and concrete revision "
            "recommendations."
        ),
        agent=content_critic,
        context=[research_task, writing_task],
        callback=make_stage_callback("Critique", on_stage_complete),
    )
    optimization_task = Task(
        description=(
            "Revise the first draft using the research brief and critique. "
            "Preserve supported facts, address the prioritized feedback, and "
            "return a polished post that is clear, authentic, concise, and "
            "ready for a human to publish. Do not claim that it has been posted."
        ),
        expected_output=(
            "The final LinkedIn post in clean, copy-ready text, plus a brief "
            "change summary and any fact-check caveat that remains."
        ),
        agent=content_optimizer,
        context=[research_task, writing_task, critique_task],
        callback=make_stage_callback("Optimization", on_stage_complete),
    )
    scheduling_task = Task(
        description=(
            "Prepare publication guidance for the optimized LinkedIn post. "
            "Recommend 1-2 testable posting windows and days, explicitly state "
            "that times are in the target audience's local timezone unless "
            "another timezone is known, and explain that performance should be "
            "validated against the account's own analytics. Include a brief "
            "pre-publication checklist. Do not claim to access a calendar, "
            "schedule, or publish the post."
        ),
        expected_output=(
            "A publication-ready handoff containing the final post, suggested "
            "posting windows with timezone assumptions, a concise checklist, "
            "and a clear statement that no post was actually scheduled."
        ),
        agent=scheduling_agent,
        context=[
            research_task,
            writing_task,
            critique_task,
            optimization_task,
        ],
        callback=make_stage_callback("Scheduling", on_stage_complete),
    )

    return Crew(
        agents=[
            trend_researcher,
            content_writer,
            content_critic,
            content_optimizer,
            scheduling_agent,
        ],
        tasks=[
            research_task,
            writing_task,
            critique_task,
            optimization_task,
            scheduling_task,
        ],
        process=Process.sequential,
        verbose=True,
        memory=True,
        # Stay below the common AI Studio free-tier request-per-minute limit.
        max_rpm=4,
        # Gemini embeddings keep CrewAI memory on the configured AI Studio key.
        embedder={
            "provider": "google-vertex",
            "config": {
                "model_name": "gemini-embedding-001",
                "api_key": ai_studio_api_key,
                "task_type": "RETRIEVAL_DOCUMENT",
            },
        },
    )


def main() -> int:
    """Run the workflow for one user-supplied topic."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        ai_studio_api_key = configure_api_keys()
        topic = input("Enter the LinkedIn topic or niche: ").strip()
        if not topic:
            print("A topic or niche is required.", file=sys.stderr)
            return 2

        crew = build_crew(ai_studio_api_key)
        result = crew.kickoff(inputs={"topic": topic})
        print(f"\n{STAGE_SEPARATOR}\nPUBLISH-READY HANDOFF\n{STAGE_SEPARATOR}")
        print(result.raw)
        return 0
    except ConfigurationError as exc:
        LOGGER.error("%s", exc)
        return 2
    except EOFError:
        LOGGER.error("No topic was provided.")
        return 2
    except KeyboardInterrupt:
        print("\nRun cancelled.", file=sys.stderr)
        return 130
    except Exception:
        # Keep provider/tool details in the log while giving the user next steps.
        LOGGER.exception("The content pipeline failed.")
        print(
            "The pipeline could not complete. Check the API keys, Gemini/Serper "
            "quota and availability, and the logged error above.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
