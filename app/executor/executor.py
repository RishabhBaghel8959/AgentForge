from app.planner.planner import Planner


class AgentExecutor:

    def __init__(self):

        self.planner = Planner()

    def run(self, request):

        plan = self.planner.create_plan(request)

        return {
            "status": "success",
            "request": request,
            "execution_plan": plan
        }