import { Link, useNavigate } from "react-router-dom";

function Navbar() {
    const navigate = useNavigate();

    const logout = () => {
        localStorage.removeItem("token");
        navigate("/login");
    };

    return (
        <nav className="navbar">
            <div className="logo">
                Muni48
            </div>

            <div className="nav-links">
                <Link to="/dashboard">
                    Dashboard
                </Link>

                <Link to="/news">
                    News
                </Link>

                <Link to="/writing">
                    Writing
                </Link>

                <Link to="/essay">
                    Essay
                </Link>

                <button onClick={logout}>
                    Logout
                </button>
            </div>
        </nav>
    );
}

export default Navbar;