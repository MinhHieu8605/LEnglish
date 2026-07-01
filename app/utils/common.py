from fastapi import HTTPException,status


def raise_not_found(message: str = "record not found"):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

def raise_bad_request(message: str = "Bad request"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)