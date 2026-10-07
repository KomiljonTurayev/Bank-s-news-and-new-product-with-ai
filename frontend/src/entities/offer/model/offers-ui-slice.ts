import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type OffersUiState = {
  product: string;
  search: string;
  sort: string;
  view: string;
  compareCodes: string[];
};

const initialState: OffersUiState = {
  product: "deposit",
  search: "",
  sort: "best",
  view: "cards",
  compareCodes: [],
};

// Bozor taklifi filtr/saralash/ko'rinish holati — tab/qidiruv/saralash
// asosiy sahifada (OffersSection) joylashgan, lekin holat butun ilova
// darajasida (redux) saqlanadi.
const offersUiSlice = createSlice({
  name: "offersUi",
  initialState,
  reducers: {
    setProduct: (state, action: PayloadAction<string>) => {
      state.product = action.payload;
    },
    setSearch: (state, action: PayloadAction<string>) => {
      state.search = action.payload;
    },
    setSort: (state, action: PayloadAction<string>) => {
      state.sort = action.payload;
    },
    setView: (state, action: PayloadAction<string>) => {
      state.view = action.payload;
    },
    toggleCompare: (state, action: PayloadAction<string>) => {
      const code = action.payload;
      const idx = state.compareCodes.indexOf(code);
      if (idx === -1) state.compareCodes.push(code);
      else state.compareCodes.splice(idx, 1);
    },
    clearCompare: state => {
      state.compareCodes = [];
    },
    // Brend bosilib bosh sahifaga qaytilganda filtr/ko'rinish holati
    // boshlang'ichiga qaytadi — home yangi holatda ochiladi.
    resetOffersUi: () => initialState,
  },
});

export const {
  setProduct,
  setSearch,
  setSort,
  setView,
  toggleCompare,
  clearCompare,
  resetOffersUi,
} = offersUiSlice.actions;
export const offersUiReducer = offersUiSlice.reducer;
