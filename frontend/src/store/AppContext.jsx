import { createContext } from 'react';

const AppContext = createContext({
  sessions: [],
  setSessions: () => {},
  activeTenant: '',
  setActiveTenant: () => {},
  tenants: [],
});

export default AppContext;
