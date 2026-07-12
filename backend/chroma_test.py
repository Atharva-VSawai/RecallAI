from dotenv import load_dotenv; load_dotenv()
from db.chroma import chroma_store, chroma_search

try:
    chroma_store('test decision about python migration', 'test')
    print('Store OK')
    results = chroma_search('python')
    print(f'Search OK: {len(results)} results')
    if results:
        print(results[0]['page_content'][:80])
except Exception as e:
    print(f'ERROR: {e}')
