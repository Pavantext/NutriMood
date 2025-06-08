from utils.pinecone_helper import get_new_index, delete_all_data

def main():
    # Get the index
    index = get_new_index()
    
    # Delete all data
    delete_all_data(index)

if __name__ == "__main__":
    main() 