// Navbar Component with Voice Answer Mode toggle

import { NavLink } from 'react-router-dom';
import { Navbar, Nav, Container } from 'react-bootstrap';
import { useVoiceMode } from '../context/VoiceContext';

const AppNavbar = () => {
    const { voiceEnabled, toggleVoice } = useVoiceMode();

    return (
        <Navbar className="main-navbar" expand="lg" sticky="top">
            <Container>
                <Navbar.Brand as={NavLink} to="/">
                    ⚡ Invoice Manager
                </Navbar.Brand>
                <Navbar.Toggle aria-controls="main-nav" />
                <Navbar.Collapse id="main-nav" >
                    <Nav className="ms-auto gap-2 align-items-center" >
                        <Nav.Link as={NavLink} to="/" end className='px-3'>
                            Dashboard
                        </Nav.Link>
                        <Nav.Link as={NavLink} to="/documents" className='px-3'>
                            Documents
                        </Nav.Link>
                        <button
                            className={`voice-mode-toggle ${voiceEnabled ? 'active' : ''}`}
                            onClick={toggleVoice}
                            title={voiceEnabled ? 'Voice answers ON — click to mute' : 'Voice answers OFF — click to enable'}
                        >
                            {voiceEnabled ? '🔊' : '🔇'}
                            <span className="voice-mode-label">
                                {voiceEnabled ? 'Voice On' : 'Voice Off'}
                            </span>
                        </button>
                    </Nav>
                </Navbar.Collapse>
            </Container>
        </Navbar>
    );
};

export default AppNavbar;
