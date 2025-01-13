import functools

def remove_prefix(prefix: str):
    """
    Decorator to remove a specified prefix from the return value of a function.

    Args:
        prefix (str): The prefix to remove.

    Returns:
        Callable: The wrapped function.
    """
    def decorator_remove_prefix(func):
        @functools.wraps(func)
        def wrapper_remove_prefix(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, str) and result.startswith(prefix):
                return result[len(prefix):].lstrip("/")  # Remove prefix and leading slash
            return result
        return wrapper_remove_prefix
    return decorator_remove_prefix