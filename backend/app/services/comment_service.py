from sqlalchemy.orm import Session
from app.models.comment import Comment


def add_comment(db, report_id, user_id, text, visibility="public"):
    comment = Comment(expense_report_id=report_id, author_user_id=user_id, text=text, visibility=visibility)
    db.add(comment)
    db.commit()
    return comment
