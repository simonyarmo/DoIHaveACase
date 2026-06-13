import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import CurrentUserDep, DbDep, get_case_or_404
from models.expense import CaseExpense
from schemas.expenses import ExpenseCreate, ExpenseOut, ExpenseUpdate

router = APIRouter(prefix="/cases/{case_id}/expenses", tags=["expenses"])


async def _get_expense_or_404(db: DbDep, case_id: uuid.UUID, expense_id: str) -> CaseExpense:
    try:
        expense_uuid = uuid.UUID(expense_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    expense = await db.get(CaseExpense, expense_uuid)
    if expense is None or expense.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.get("", response_model=list[ExpenseOut])
async def list_expenses(case_id: str, current_user: CurrentUserDep, db: DbDep) -> list[ExpenseOut]:
    case = await get_case_or_404(db, case_id, current_user.id)
    expenses = (
        await db.execute(select(CaseExpense).where(CaseExpense.case_id == case.id).order_by(CaseExpense.date.desc()))
    ).scalars().all()
    return [ExpenseOut.model_validate(expense) for expense in expenses]


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(case_id: str, payload: ExpenseCreate, current_user: CurrentUserDep, db: DbDep) -> ExpenseOut:
    case = await get_case_or_404(db, case_id, current_user.id)
    expense = CaseExpense(case_id=case.id, **payload.model_dump())
    db.add(expense)
    await db.commit()
    return ExpenseOut.model_validate(expense)


@router.put("/{expense_id}", response_model=ExpenseOut)
async def update_expense(case_id: str, expense_id: str, payload: ExpenseUpdate, current_user: CurrentUserDep, db: DbDep) -> ExpenseOut:
    case = await get_case_or_404(db, case_id, current_user.id)
    expense = await _get_expense_or_404(db, case.id, expense_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)

    await db.commit()
    return ExpenseOut.model_validate(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(case_id: str, expense_id: str, current_user: CurrentUserDep, db: DbDep) -> None:
    case = await get_case_or_404(db, case_id, current_user.id)
    expense = await _get_expense_or_404(db, case.id, expense_id)

    await db.delete(expense)
    await db.commit()
