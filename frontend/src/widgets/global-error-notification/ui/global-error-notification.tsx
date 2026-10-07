import { useEffect } from "react";
import { notifications } from "@mantine/notifications";
import { useDispatch, useSelector } from "react-redux";

// FSD: quyqi slice app qatlamidan faqat TIPLARNI oladi (import type kompilyatsiyada o'chadi).
import type { AppDispatch, RootState } from "@/app/store";
import { clearError } from "@/shared/model";

export const GlobalErrorNotification = () => {
  const message = useSelector((state: RootState) => state.error.message);
  const dispatch = useDispatch<AppDispatch>();

  useEffect(() => {
    if (message) {
      notifications.show({
        title: "Xatolik",
        message,
        color: "red",
        autoClose: 4000,
      });
      dispatch(clearError());
    }
  }, [message, dispatch]);

  return null;
};
