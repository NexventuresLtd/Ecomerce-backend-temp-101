from fastapi import Depends
from typing import Annotated
from Endpoints.Auth.normal_login import get_current_user  

user_dependency = Annotated[dict, Depends(get_current_user)]

