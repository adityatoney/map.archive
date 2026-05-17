import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Patient } from "@/lib/api-client";

interface PatientStore {
  selectedPatientId: string | null;
  patients: Patient[];
  latestSessionId: string | null;
  setSelectedPatientId: (id: string | null) => void;
  setPatients: (patients: Patient[]) => void;
  setLatestSessionId: (id: string | null) => void;
}

export const usePatientStore = create<PatientStore>()(
  persist(
    (set) => ({
      selectedPatientId: null,
      patients: [],
      latestSessionId: null,
      setSelectedPatientId: (id) => set({ selectedPatientId: id }),
      setPatients: (patients) => set({ patients }),
      setLatestSessionId: (id) => set({ latestSessionId: id }),
    }),
    { name: "medical-analytics-platform-patient-store" }
  )
);
