def ensure_request_user_id_matches_data(request):
    """Ensures that user_id in request.data is request.user.id
    Parameters
    ----------
    request

    Returns
    -------

    """
    data = request.data.copy()
    data["user_id"] = request.user.id
    request._full_data = data
