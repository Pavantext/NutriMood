from dotenv import load_dotenv
from utils.pinecone_helper_new import get_new_index

load_dotenv()

# This will create the new index if it doesn't exist
index = get_new_index()
print("New index created successfully!")