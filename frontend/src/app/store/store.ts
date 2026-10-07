import { configureStore } from "@reduxjs/toolkit";

import { errorReducer } from "@/shared/model";
import { offersUiReducer } from "@/entities/offer";

export const store = configureStore({
  reducer: {
    error: errorReducer,
    offersUi: offersUiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
