import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
} from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";

import Dashboard from "./pages/Dashboard";
import News from "./pages/News";
import MCQs from "./pages/MCQs";
import Writing from "./pages/Writing";
import Essays from "./pages/Essays";

function App() {
    return (
        <BrowserRouter>
            <Routes>

                {/* Default */}
                <Route
                    path="/"
                    element={
                        <Navigate
                            to="/login"
                            replace
                        />
                    }
                />

                {/* Authentication */}
                <Route
                    path="/login"
                    element={<Login />}
                />

                <Route
                    path="/signup"
                    element={<Signup />}
                />

                {/* Main */}
                <Route
                    path="/dashboard"
                    element={<Dashboard />}
                />

                {/* Current Affairs */}
                <Route
                    path="/news"
                    element={<News />}
                />

                {/* MCQ Practice */}
                <Route
                    path="/mcqs"
                    element={<MCQs />}
                />

                {/* Answer Writing */}
                <Route
                    path="/writing"
                    element={<Writing />}
                />

                {/* Essay Practice */}
                <Route
                    path="/essays"
                    element={<Essays />}
                />

                {/* Unknown */}
                <Route
                    path="*"
                    element={
                        <Navigate
                            to="/login"
                            replace
                        />
                    }
                />

            </Routes>
        </BrowserRouter>
    );
}

export default App;

