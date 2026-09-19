from ml_engine import MLEngine

class RiskEngine:
    @staticmethod
    def calculate(patient, pressure_zones, temp_left, temp_right, gait_data):
        """
        Delegates risk level prediction, composite score calculation, and feature breakdown
        to the machine-learning engine (MLEngine).
        """
        return MLEngine.predict(patient, pressure_zones, temp_left, temp_right, gait_data)
