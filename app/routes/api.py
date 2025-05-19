from fastapi import APIRouter, HTTPException
from ..controllers.user_controller import UserController
from ..controllers.study_planner_controller import StudyPlannerController
from ..models.user import User
from ..models.study_plan import StudyPlanRequest, StudyPlanResponse

router = APIRouter()

@router.get("/users", response_model=list[User])
def get_users():
    return UserController.get_users()

@router.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    user = UserController.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/users", response_model=User)
def create_user(user: User):
    return UserController.create_user(user)

@router.post("/v1/study-plan", response_model=StudyPlanResponse)
def generate_study_plan(plan_request: StudyPlanRequest):
    """
    Generate a personalized study plan based on subjects, exam dates, and available hours.
    """
    try:
        study_plan = StudyPlannerController.generate_study_plan(plan_request)
        return study_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating study plan: {str(e)}") 