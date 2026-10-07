import { Button, Container, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <Container size="sm" py="xl">
      <Stack align="center" gap="md">
        <Title order={1}>404</Title>
        <Text c="dimmed">Siz qidirayotgan sahifa topilmadi.</Text>
        <Button component={Link} to="/">
          Bosh sahifaga
        </Button>
      </Stack>
    </Container>
  );
}
