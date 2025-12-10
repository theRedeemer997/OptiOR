import axios from "axios";
import {
  CreateCaseRequest,
  PredictionRequest,
  PredictionResponse,
  SurgeryCase,
} from "@/components/types";

const API_BASE_URL = "http://127.0.0.1:5000/api";

export const api = {
  getCases: async (): Promise<SurgeryCase[]> => {
    const response = await axios.get(`${API_BASE_URL}/cases`);
    return response.data;
  },

  getPrediction: async (
    data: PredictionRequest
  ): Promise<PredictionResponse> => {
    const response = await axios.post(
      `${API_BASE_URL}/predict_suggestion`,
      data
    );
    return response.data;
  },

  getAveragePrediction: async (
    service: string,
    date?: string
  ): Promise<{ predicted_duration: number; source?: string }> => {
    const response = await axios.post(`${API_BASE_URL}/predict_average`, {
      service,
      date,
    });
    return response.data;
  },

  createCase: async (data: CreateCaseRequest) => {
    const response = await axios.post(`${API_BASE_URL}/cases`, data);
    return response.data;
  },

  updateCase: async (id: number, data: Partial<CreateCaseRequest>) => {
    const response = await axios.put(`${API_BASE_URL}/cases/${id}`, data);
    return response.data;
  },

  deleteCase: async (id: number) => {
    const response = await axios.delete(`${API_BASE_URL}/cases/${id}`);
    return response.data;
  },

  getAnalyticsStatus: async (period: string = "all") => {
    const response = await axios.get(`${API_BASE_URL}/analytics/status`, {
      params: { period },
    });
    return response.data;
  },

  getAnalyticsCharts: async (period: string = "all") => {
    const response = await axios.get(`${API_BASE_URL}/analytics`, {
      params: { period },
    });
    return response.data;
  },

  getDoctors: async () => {
    const response = await axios.get(`${API_BASE_URL}/doctors`);
    return response.data;
  },
};
