from fastapi import APIRouter

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("")
async def list_roles():
    return [
        {"code": "administrator", "name": "Administrator"},
        {"code": "approver", "name": "Approver"},
        {"code": "employee", "name": "Employee"},
    ]
