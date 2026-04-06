import { createContext, useContext, useState, useEffect } from 'react';

type Gender = 'men' | 'women';

interface GenderContextType {
    selectedGender: Gender;
    setGender: (gender: Gender) => void;
}

const GenderContext = createContext<GenderContextType | undefined>(undefined);

export function GenderProvider({ children }: { children: React.ReactNode }) {
    const [selectedGender, setSelectedGender] = useState<Gender>('women');

    useEffect(() => {
        try {
            const saved = localStorage.getItem('confit_gender');
            if (saved === 'men' || saved === 'women') setSelectedGender(saved);
        } catch {
            /* ignore */
        }
    }, []);

    const setGender = (gender: Gender) => {
        setSelectedGender(gender);
        try {
            localStorage.setItem('confit_gender', gender);
        } catch {
            /* ignore */
        }
    };

    return (
        <GenderContext.Provider value={{ selectedGender, setGender }}>
            {children}
        </GenderContext.Provider>
    );
}

export function useGender() {
    const context = useContext(GenderContext);
    if (context === undefined) {
        throw new Error('useGender must be used within a GenderProvider');
    }
    return context;
}
