export interface SurgeryCase {
  id: number;
  title: string;
  start: string; // ISO date string
  end: string | null;
  extendedProps: {
    or_suite: string;
    service: string;
    booked_time: number;
    actual_duration: number;
    patient_name: string;
    is_prediction: boolean;
    doctor_name?: string;
  };
}

export interface PredictionRequest {
  date: string;
  service: string;
  booked_time: number;
  patient_name: string;
  or_suite: string;
}

export interface PredictionResponse {
  predicted_duration: number;
}

export interface CreateCaseRequest {
  date: string;
  service: string;
  booked_time: number;
  patient_name: string;
  or_suite: string;
  wheels_in: string; // Specific start time
  wheels_out: string; // Calculated end time
  actual_duration: number;
  doctor_name?: string;
}
