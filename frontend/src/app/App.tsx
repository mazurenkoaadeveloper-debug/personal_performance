import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";


export function App() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static">
        <Toolbar>
          <Typography component="span" sx={{ flexGrow: 1, fontWeight: 700 }}>
            GitLab Activity
          </Typography>
          <Stack component="nav" direction="row" spacing={1} aria-label="Основная навигация">
            <Button color="inherit" href="/developers">
              Разработчики
            </Button>
            <Button color="inherit" href="/synchronization">
              Синхронизация
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: 6 }}>
        <Typography component="h1" variant="h3" gutterBottom>
          GitLab Developer Activity Analytics
        </Typography>
        <Typography color="text.secondary">
          Фактическая аналитика активности в GitLab без рейтингов и оценок производительности.
        </Typography>
      </Container>
    </Box>
  );
}
