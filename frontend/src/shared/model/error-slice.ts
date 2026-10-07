import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type ErrorState = {
  message: string | null;
};

const initialState: ErrorState = {
  message: null,
};

const errorSlice = createSlice({
  name: "error",
  initialState,
  reducers: {
    setError: (state, action: PayloadAction<string>) => {
      state.message = action.payload;
    },
    clearError: state => {
      state.message = null;
    },
  },
});

export const { setError, clearError } = errorSlice.actions;
export const errorReducer = errorSlice.reducer;
