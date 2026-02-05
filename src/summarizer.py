import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv() 

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# configure small, fast model
llm = ChatOpenAI(
    model_name=os.environ.get('OPENAI_MODEL', 'gpt-4.1-nano'), 
    temperature=0.1, 
    openai_api_key=OPENAI_API_KEY
)

# Prompt for factual summary
summary_prompt = PromptTemplate(
    input_variables=["article_text"],
    template=(
        "You are a concise, factual summarizer.\n"
        "Summarize the following article in neutral, factual language in up to 5 sentences."
        " List the main facts and key numbers.\n\nArticle:\n{article_text}\n\nSummary:"
    )
)

# Modern RunnableSequence syntax
summary_chain = summary_prompt | llm

# Prompt for converting summary to a 30-45s news script (80-120 words target)
script_prompt = PromptTemplate(
    input_variables=["headline", "summary"],
    template=(
        "You are a professional news writer.\n"
        "Given this HEADLINE and SUMMARY, write a spoken news-anchor script suitable for a 30-45 second read (about 80-120 words).\n"
        "Tone: professional, conversational, neutral. Start with a short headline line, then two short paragraphs, end with a 1-sentence closing.\n\n"
        "HEADLINE: {headline}\n\nSUMMARY: {summary}\n\nSCRIPT:"
    )
)

# Modern RunnableSequence syntax
script_chain = script_prompt | llm


async def summarize_article(article_text: str) -> str:
    """Return a concise, factual summary of an article (async)."""
    response = await summary_chain.ainvoke({"article_text": article_text})
    # Extract text from AIMessage object
    return response.content if hasattr(response, 'content') else str(response)


async def generate_script(headline: str, summary: str) -> str:
    """Return a 30-45s news-anchor style script (async)."""
    response = await script_chain.ainvoke({"headline": headline, "summary": summary})
    # Extract text from AIMessage object
    return response.content if hasattr(response, 'content') else str(response)