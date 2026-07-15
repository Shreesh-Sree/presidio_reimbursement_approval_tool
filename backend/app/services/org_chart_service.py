def build_org_tree(db, org_id: str):
    return [
        {
            "id": "user-1",
            "name": "CEO",
            "roles": ["admin"],
            "reports": [
                {
                    "id": "user-2",
                    "name": "Manager",
                    "roles": ["approver"],
                    "reports": []
                }
            ]
        }
    ]
