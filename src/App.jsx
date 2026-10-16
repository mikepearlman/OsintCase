import { useEffect, useState } from 'react';
import { bridgeRequest } from './components/PhoneArchive.jsx';
import { useProject } from './context/ProjectContext.jsx';
import { useAppConfig } from './context/AppConfigContext.jsx';
import Landing from './components/Landing.jsx';
import ProjectView from './components/ProjectView.jsx';
import Welcome from './components/Welcome.jsx';

export default function App() {
  const { project, isEncrypted, openProjectFromSnapshot } = useProject();
  const [bridgeError, setBridgeError] = useState('');
  useEffect(() => {
    if (project) return;
    let live = true;
    bridgeRequest('/bridge/saved').then(snapshot => {
      if (live) openProjectFromSnapshot({ snapshot });
    }).catch(e => { if (live) setBridgeError(e.message); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    if (project?.id !== 'phone-evidence' || isEncrypted) return;
    const timer = setTimeout(() => bridgeRequest('/bridge/save', project).then(() => setBridgeError('')).catch(e => setBridgeError('Local save failed: ' + e.message)), 1200);
    return () => clearTimeout(timer);
  }, [project, isEncrypted]);
  const { loaded, mapProviderSource } = useAppConfig();

  // Wait until the config layer has tried to read localStorage + the config
  // file. Showing nothing for one frame beats flashing the welcome screen
  // to an existing user.
  if (!loaded) return null;

  // First-run detection: the user has never explicitly picked a map provider.
  // We intentionally do NOT factor in whether an API key exists — a Docker
  // user with a key in .env should still get to choose OpenStreetMap vs
  // Google Maps. When they pick Google, the Welcome screen skips the
  // key-entry step because the key is already configured. A Clear-All-Data
  // wipe removes the provider choice too, so it also lands here again.
  const isFirstRun = mapProviderSource === null;
  if (isFirstRun) return <Welcome />;

  return <>{bridgeError && <p role="alert" className="phone-start-error">{bridgeError}</p>}{project ? <ProjectView /> : <Landing />}</>;
}
