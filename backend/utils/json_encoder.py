import json
import numpy as np
import numpy
from datetime import datetime

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types and other non-serializable objects"""

    def default(self, obj):
        # Handle numpy types
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)

        # Handle datetime objects
        elif isinstance(obj, datetime):
            return obj.isoformat()

        # Handle bytes
        elif isinstance(obj, bytes):
            return obj.decode('utf-8')

        # Let the base class default method raise the TypeError
        return super().default(obj)

def json_dumps(data, **kwargs):
    """Wrapper for json.dumps that uses NumpyEncoder by default"""
    if 'cls' not in kwargs:
        kwargs['cls'] = NumpyEncoder
    return json.dumps(data, **kwargs)

def convert_numpy_types(obj):
    """Recursively convert numpy types in a dictionary or list to native Python types."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, (numpy.int64, numpy.int32, np.integer)):
        return int(obj)
    elif isinstance(obj, (numpy.float64, numpy.float32, np.floating)):
        return float(obj)
    elif isinstance(obj, (numpy.ndarray, np.ndarray)):
        return obj.tolist()
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj
