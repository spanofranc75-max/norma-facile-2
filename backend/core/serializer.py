"""MongoDB document serializer — converts ObjectId and datetime to JSON-safe types."""

from bson import ObjectId
from datetime import datetime


def serialize_doc(doc):
    """Recursively convert ObjectId → str, datetime → ISO string.
    Works on dicts, lists, and nested structures.
    Returns None if doc is None.
    """
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == "_id" and isinstance(value, ObjectId):
                result["_id"] = str(value)
                continue
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                result[key] = serialize_doc(value)
            else:
                result[key] = value
        return result
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc


def serialize_list(docs):
    """Serialize a list of MongoDB documents."""
    return [serialize_doc(d) for d in docs]
