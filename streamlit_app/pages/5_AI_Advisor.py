import streamlit as st
from snowflake.core import Root

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")

st.title("Customer 360 AI Advisor")
st.caption("Ask natural-language questions about customers, churn risk, sentiment, and get action recommendations")

conn = st.connection("snowflake")
session = conn.session()
root = Root(session)

AGENT_NAME = "CUSTOMER_360.APP.CUSTOMER_360_AGENT"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Example prompts
with st.sidebar:
    st.header("Example Questions")
    examples = [
        "How many high-risk churn customers are in the Premium segment?",
        "What is the average sentiment score by customer segment?",
        "Show me the top 10 customers by churn risk with their next best action",
        "What are the most common actions recommended for customers with negative sentiment?",
        "Search for customer calls about policy renewal disputes",
        "How many customers have more than 2 complaints?",
        "What is the churn risk distribution across segments?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about your customers..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Generate response for the latest user message
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                agent = root.cortex_agents[AGENT_NAME]
                response = agent.complete(
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ]
                )

                # Extract text from agent response
                assistant_text = ""
                if hasattr(response, "messages"):
                    for msg in response.messages:
                        if hasattr(msg, "content"):
                            assistant_text += msg.content
                elif hasattr(response, "content"):
                    assistant_text = response.content
                else:
                    assistant_text = str(response)

                st.markdown(assistant_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_text}
                )
            except Exception as e:
                error_msg = f"Error communicating with the AI advisor: {str(e)}"
                st.error(error_msg)
                # Fallback: run a direct SQL query if the agent is unavailable
                st.info("Falling back to direct SQL query...")
                try:
                    user_q = st.session_state.messages[-1]["content"]
                    fallback = conn.query(f"""
                        SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b',
                            'You are a customer analytics assistant. Answer this question using your knowledge of insurance/lending customer data: {user_q.replace("'", "''")}'
                        ) AS RESPONSE
                    """)
                    fallback_text = fallback["RESPONSE"].iloc[0]
                    st.markdown(fallback_text)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": fallback_text}
                    )
                except Exception as e2:
                    st.error(f"Fallback also failed: {str(e2)}")
