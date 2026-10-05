from rest_framework.response import Response
from rest_framework.views import APIView
from routes.services import TripException, TripPlanner


class TripPlanView(APIView):
    """GET /api/routes/route/?start=New York, NY&finish=Los Angeles, CA"""

    def get(self, request):
        start, finish = request.query_params.get("start"), request.query_params.get("finish")
        if not start or not finish:
            return Response({"error": "start and finish are required."}, status=400)
        try:
            return Response(TripPlanner().plan(start, finish).to_dict())
        except TripException as e:
            return Response({"error": str(e)}, status=e.status)