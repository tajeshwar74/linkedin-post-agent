"""Streamlit dashboard for the LinkedIn content manager CrewAI pipeline."""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from linkedin_content_manager import (
    ConfigurationError,
    build_crew,
    configure_api_keys,
)


LOGGER = logging.getLogger("linkedin_content_dashboard")
STAGES = ("Research", "Writing", "Critique", "Optimization", "Scheduling")

st.set_page_config(
    page_title="LinkedIn Content Studio",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --maroon: #70263c;
        --maroon-dark: #4d1729;
        --maroon-soft: #f5edf0;
        --ink: #292329;
        --muted: #70676b;
        --line: #eadfe3;
        --paper: #ffffff;
    }
    .stApp {
        background: var(--paper);
        color: var(--ink);
    }
    [data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0.96);
    }
    [data-testid="stToolbar"],
    .stDeployButton {
        display: none;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 1120px;
        padding-top: 2.4rem;
        padding-bottom: 4rem;
    }
    .eyebrow {
        color: var(--maroon);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }
    .stApp .hero-title {
        color: #4d1729;
        font-size: clamp(2.2rem, 5vw, 3.5rem);
        font-weight: 750;
        letter-spacing: -0.045em;
        line-height: 1.08;
        margin: 0;
    }
    .hero-copy {
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.7;
        max-width: 720px;
        margin: 1rem 0 1.8rem;
    }
    .section-title {
        color: var(--maroon-dark);
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0.4rem 0 0.25rem;
    }
    div[data-testid="stForm"] {
        border: 1px solid var(--line);
        border-radius: 16px;
        background: #fff;
        padding: 1.3rem 1.4rem 0.8rem;
        box-shadow: 0 10px 32px rgba(77, 23, 41, 0.055);
    }
    div[data-testid="stTextArea"] label,
    div[data-testid="stTextInput"] label {
        color: var(--ink);
        font-weight: 650;
    }
    div[data-testid="stTextArea"] textarea {
        border-color: var(--line);
        border-radius: 10px;
        background: #fff;
        color: var(--ink);
    }
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #8a8084;
        opacity: 1;
    }
    div[data-testid="stTextArea"] textarea:focus {
        border-color: var(--maroon);
        box-shadow: 0 0 0 1px var(--maroon);
    }
    .stButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        background: var(--maroon);
        border: 1px solid var(--maroon);
        border-radius: 9px;
        color: white;
        font-weight: 650;
        min-height: 2.8rem;
        padding: 0.55rem 1.1rem;
    }
    .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: var(--maroon-dark);
        border-color: var(--maroon-dark);
        color: white;
    }
    div[data-testid="stAlert"] {
        border-radius: 10px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 13px;
    }
    .stage-label {
        color: var(--maroon);
        font-size: 0.75rem;
        font-weight: 750;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 0.35rem;
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            padding: 1.4rem 1rem 3rem;
        }
        div[data-testid="stForm"] {
            padding: 1rem 0.9rem 0.6rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="eyebrow">AI-powered publishing workflow</div>
    <h1 class="hero-title">LinkedIn Content Studio</h1>
    <p class="hero-copy">
        Turn an idea into a researched, reviewed, and publish-ready LinkedIn
        post. Five focused AI stages work in sequence, with the results shown
        here as they complete.
    </p>
    """,
    unsafe_allow_html=True,
)

with st.form("content_request", clear_on_submit=False):
    st.markdown('<div class="section-title">Start with a topic</div>', unsafe_allow_html=True)
    topic = st.text_area(
        "Topic or niche",
        placeholder="For example: practical uses of AI agents in customer support",
        height=110,
        max_chars=500,
        help="Be specific about the subject you want researched and turned into a post.",
    )
    submitted = st.form_submit_button(
        "Create LinkedIn post",
        type="primary",
        width="content",
    )

if submitted:
    clean_topic = topic.strip()
    if not clean_topic:
        st.error("Enter a topic or niche to start the workflow.")
    else:
        st.session_state["stage_outputs"] = {}
        st.session_state.pop("final_output", None)
        st.session_state.pop("pipeline_error", None)

        st.markdown('<div class="section-title">Your content workflow</div>', unsafe_allow_html=True)
        status = st.status(
            "Preparing the five-stage pipeline",
            expanded=True,
        )
        progress = st.progress(0, text="Waiting for the research stage")
        stage_area = st.container()
        stage_slots = {stage: stage_area.empty() for stage in STAGES}

        def display_stage(stage: str, task_output: Any) -> None:
            """Render each completed task into its persistent stage slot."""
            raw_output = str(task_output.raw)
            st.session_state["stage_outputs"][stage] = raw_output
            with stage_slots[stage].container(border=True):
                st.markdown(
                    f'<div class="stage-label">{stage}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(raw_output)
            completed_count = len(st.session_state["stage_outputs"])
            progress.progress(
                completed_count / len(STAGES),
                text=f"{stage} complete · {completed_count} of {len(STAGES)} stages",
            )
            if completed_count < len(STAGES):
                status.update(
                    label=f"{stage} complete; continuing to the next stage",
                    state="running",
                )

        try:
            api_key = configure_api_keys()
            crew = build_crew(api_key, on_stage_complete=display_stage)
            result = crew.kickoff(inputs={"topic": clean_topic})
            st.session_state["final_output"] = str(result.raw)
            progress.progress(1.0, text="All five stages are complete")
            status.update(
                label="Content workflow complete",
                state="complete",
                expanded=False,
            )
        except ConfigurationError as exc:
            LOGGER.error("%s", exc)
            st.session_state["pipeline_error"] = str(exc)
            status.update(label="Configuration required", state="error")
        except Exception as exc:
            LOGGER.exception("The dashboard content pipeline failed.")
            st.session_state["pipeline_error"] = f"{type(exc).__name__}: {exc}"
            status.update(label="Content workflow stopped", state="error")

if st.session_state.get("pipeline_error"):
    st.error(st.session_state["pipeline_error"])

stage_outputs = st.session_state.get("stage_outputs", {})
if stage_outputs and not submitted:
    st.markdown('<div class="section-title">Completed stages</div>', unsafe_allow_html=True)
    for stage in STAGES:
        if stage not in stage_outputs:
            continue
        with st.container(border=True):
            st.markdown(
                f'<div class="stage-label">{stage}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(stage_outputs[stage])

final_output = st.session_state.get("final_output")
if final_output:
    st.markdown('<div class="section-title">Publish-ready handoff</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(final_output)
    st.caption(
        "Review source claims and timing recommendations before publishing. "
        "This dashboard prepares content but does not publish or schedule it."
    )
