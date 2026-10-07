import { Alert, Button, Code, Container, Group, Stack, Title } from "@mantine/core";

import { errorMessage } from "./error-message";

type Props = {
  error: unknown;
  reset?: () => void;
};

export const ErrorFallback = ({ error, reset }: Props) => {
  const isDev = import.meta.env.DEV;
  const message = errorMessage(error);
  const stack = error instanceof Error ? error.stack : undefined;

  return (
    <Container size="sm" py="xl">
      <Stack>
        <Title order={2}>Nimadir xato ketdi</Title>
        <Alert color="red" variant="light">
          {message}
        </Alert>
        {isDev && stack && (
          <Code block style={{ maxHeight: 240, overflow: "auto" }}>
            {stack}
          </Code>
        )}
        <Group>
          {reset && (
            <Button onClick={reset} variant="light">
              Qayta urinish
            </Button>
          )}
          <Button onClick={() => (window.location.href = "/")}>Bosh sahifa</Button>
        </Group>
      </Stack>
    </Container>
  );
};
