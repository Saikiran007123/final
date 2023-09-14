from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
import streamlit as st
from streamlit_chat import message
from utils import *
from config import *
import snowflake.connector
import openai
from streamlit_modal import Modal
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)

# Define Snowflake connection parameters
conn = {
    "user"  : snowflake_user,
    "password": snowflake_password,
    "account": snowflake_account,
    "warehouse": snowflake_warehouse,
    "database": snowflake_database,
    "schema": snowflake_schema
}
# Create a Snowflake connection
connection = snowflake.connector.connect(**conn)

st.set_page_config(layout="wide")


# original_title1 = '<p style= "font-family:Calibri; text-align: center; color:Blue; font-size: 40px;"><b>SnowGPT</b></p>'
# st.write(original_title1 ,unsafe_allow_html=True)

# original_title1 = '<p style="font-family: Calibri; text-align: center; color: #003D79; font-size: 40px;"><b>SnowGPT</b></p>'
# st.write(original_title1, unsafe_allow_html=True)

# st.markdown(
#     """
#     <style>
#     [data-testid=stImage]{
#             justify-content: center;
#             display: flex;
#             margin-top: -86px;
#             width: 100%;
#         }
#     </style>
#     """, unsafe_allow_html=True
# )

# st.image('SnowGTP.png')

st.markdown(
    """
    <div style="display: flex; justify-content: center; margin-top: -86px;">
    <img src="https://anblicks.sharepoint.com/:i:/s/Innovation_Group/EZLgZ91J64RGqBRqFLBWniwBBeQKWAZ4Up6cgiS9j-5XhA?e=zYN3zN" width="700" />
    </div>
    """,
    unsafe_allow_html=True
)

content = '<p style="color: Black;">Unlock the Power of Snowflake: Your Personal Snowflake Documentation Chatbot. Say hello to your go-to resource for seamless access to Snowflake platform knowledge and instant answers to all your queries.</p>'
st.write(content, unsafe_allow_html=True)

# modal = Modal(key="Demo Key",title=" ")
# open_modal = st.button(label='⋮')
# right_popup_visible = False
# right_popup_content = """
# <div style= "position: fixed; bottom: 0; right: 0; width: 250px; height: 50%; background-color: white; box-shadow: -5px 0 5px rgba(0, 0, 0, 0.2);">
#          <h5 style="padding: 50px;">How to Use</h5>
#         <p>Using our chatbot is effortless – simply type in your Snowflake-related questions, and it will provide you with precise and up-to-date information from the vast Snowflake documentation.</p>  
# </div>
# """
# if open_modal:
#     right_popup_visible = not right_popup_visible

# if right_popup_visible:
#     st.write(right_popup_content, unsafe_allow_html=True)




if 'responses' not in st.session_state:
    st.session_state['responses'] = ["How can I help you"]

if 'requests' not in st.session_state:
    st.session_state['requests'] = []
    
# Iterate through query history and insert into history_table  
def add_query_history(query):
    print(query)
    cursor = connection.cursor()
    insert_query = f"INSERT INTO history_table (history) VALUES ('{query}');"
    cursor.execute(insert_query)
    cursor.close()  

#Function to fetch query history from the history_table
def fetch_query_history():
    cursor = connection.cursor()
    query = "SELECT history FROM history_table"
    cursor.execute(query)
    history = [row[0] for row in cursor]
    cursor.close()
    return history
    
def query_refiner(conversation, query):
    response = openai.Completion.create(
    model="text-davinci-003",
    prompt=f"Given the following user query and conversation log, formulate a question that would be the most relevant to provide the user with an answer from a knowledge base.\n\nCONVERSATION LOG: \n{conversation}\n\nQuery: {query}\n\nRefined Query:",
    temperature=0.7,
    max_tokens=256,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )
    return response['choices'][0]['text'] 

# # Function to check if the API key is valid
def is_valid_api_key(openai_api_key):
    return openai_api_key and openai_api_key.startswith('sk-') and len(openai_api_key) == 51

openai_api_key_container = st.sidebar.empty()                               # Create an empty container to conditionally display the API Key input field
openai_api_key = openai_api_key_container.text_input('OpenAI API Key')# Get the OpenAI API key from the user

if not openai_api_key:
    with st.sidebar:
        st.warning('Please enter your OpenAI API key!', icon='⚠️')
        
elif is_valid_api_key(openai_api_key):
    with st.sidebar:
            st.success('API Key is valid! You can proceed.', icon='✅')
            
    openai_api_key_container.empty() # Hide the openai_api_key input field
    
    openai.api_key = openai_api_key
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_api_key)

    if 'buffer_memory' not in st.session_state:
                st.session_state.buffer_memory=ConversationBufferWindowMemory(k=3,return_messages=True)

    system_msg_template = SystemMessagePromptTemplate.from_template(template="""Answer the question as truthfully as possible using the provided context, 
    and if the answer is not contained within the text below, say 'I don't know'""")

    human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
    prompt_template = ChatPromptTemplate.from_messages([system_msg_template, MessagesPlaceholder(variable_name="history"), human_msg_template])
    conversation = ConversationChain(memory=st.session_state.buffer_memory, prompt=prompt_template, llm=llm, verbose=True)

    # container for chat history
    response_container = st.container()
    # container for text box
    textcontainer = st.container()

    with textcontainer:
        query = st.chat_input("Ask me anything in snowflake: ", key="input")
        if query:
            with st.spinner("typing..."):
                conversation_string = get_conversation_string()
                # st.code(conversation_string)
                refined_query = query_refiner(conversation_string, query)
                # st.subheader("Refined Query:")
                # st.write(refined_query)
                context = find_match(refined_query)
                # print(context)  
                response = conversation.predict(input=f"Context:\n {context} \n\n Query:\n{query}")
            st.session_state.requests.append(query)
            st.session_state.responses.append(response)
            add_query_history(query)
                   
    
            
    with response_container:
            if st.session_state['responses']:
                for i in range(len(st.session_state['responses'])):
                    res = st.chat_message("assistant")
                    res.write(st.session_state['responses'][i],key=str(i))
                    # message(st.session_state['responses'][i],key=str(i))
                    if i < len(st.session_state['requests']):
                        req = st.chat_message("user")
                        req.write(st.session_state['requests'][i],is_user=True,key=str(i)+ '_user')
                        # message(st.session_state["requests"][i], is_user=True,key=str(i)+ '_user')
                    
    with st.sidebar.expander("Query History"):
        history_data = fetch_query_history()
        if history_data:
            for i, request in enumerate(history_data):
                st.write(f"{i + 1}. {request}")
        else:
            st.write("No query history available.")
            
else:
    with st.sidebar:
        st.warning('Please enter a valid open API key!', icon='⚠')
        

connection.close()

          