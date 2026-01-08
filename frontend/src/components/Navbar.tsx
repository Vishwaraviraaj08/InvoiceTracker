// Navbar Component

import { NavLink } from 'react-router-dom';
import { Navbar, Nav, Container } from 'react-bootstrap';

const AppNavbar = () => {
    return (
        <Navbar className="main-navbar" expand="lg" sticky="top">
            <Container>
                <Navbar.Brand as={NavLink} to="/">
                    ⚡ Invoice Manager
                </Navbar.Brand>
                <Navbar.Toggle aria-controls="main-nav" />
                <Navbar.Collapse id="main-nav" >
                    <Nav className="ms-auto gap-2" >
                        <Nav.Link as={NavLink} to="/" end className='px-3'>
                            Dashboard
                        </Nav.Link>
                        <Nav.Link as={NavLink} to="/documents" className='px-3'>
                            Documents
                        </Nav.Link>
                        <Nav.Link as={NavLink} to="/chat" className='px-3'>
                            Global Chat
                        </Nav.Link>
                    </Nav>
                </Navbar.Collapse>
            </Container>
        </Navbar>
    );
};

export default AppNavbar;
