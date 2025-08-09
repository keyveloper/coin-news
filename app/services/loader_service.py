from langchain_community.document_loaders import WebBaseLoader


def extractNewsMetadataFromUrl(url: str):
    loader = WebBaseLoader(url)
    docs = loader.load()

    return docs