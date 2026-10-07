import { type ComponentType, createElement } from "react";
import "@mantine/notifications/styles.css";
import "@mantine/core/styles.css";
import { createTheme, MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { emotionTransform, MantineEmotionProvider } from "@mantine/emotion";

export const withMantine = (component: ComponentType) => () => {
  const theme = createTheme({});

  return (
    <MantineProvider
      theme={theme}
      withCssVariables
      defaultColorScheme="light"
      stylesTransform={emotionTransform}>
      <MantineEmotionProvider>
        <Notifications position="top-right" />
        {createElement(component)}
      </MantineEmotionProvider>
    </MantineProvider>
  );
};
