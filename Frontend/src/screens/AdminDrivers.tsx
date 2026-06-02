import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Fingerprint, Clock, AlertTriangle, Edit2, X, Check, Plus, ExternalLink, RefreshCw, Search } from "lucide-react";
import { getUsers, updateFingerprint, getDrivingSessions, createUser, User, DrivingSession, updateUser, enrollFingerprint } from "@/api/users";
import { env } from "@/config/env";
import { listAlerts } from "@/api/alerts";
import { Alert } from "@/types/alert";
import { ImageUploader } from "@/components/ImageUploader";
import { useLanguage } from "@/i18n/LanguageContext";
import type { Appeal } from "@/types/appeal";
import { listAppealsAdmin } from "@/api/appeals";
import { calculateSafetyScore, getSafetyScoreLabel } from "@/utils/safetyScore";
import { LoadingRadar } from "@/components/LoadingRadar";

export function AdminDrivers () {
    const { t, language } = useLanguage();
    const [ drivers, setDrivers ] = useState<User[]>( [] );
    const [ loading, setLoading ] = useState( true );
    const [ selectedDriver, setSelectedDriver ] = useState<User | null>( null );
    const [ searchTerm, setSearchTerm ] = useState( "" );
    const [ allAlerts, setAllAlerts ] = useState<Alert[]>( [] );
    const [ allAppeals, setAllAppeals ] = useState<Appeal[]>( [] );

    // Add driver modal state
    const [ isAddModalOpen, setIsAddModalOpen ] = useState( false );
    const [ newDriverEmail, setNewDriverEmail ] = useState( "" );
    const [ newDriverPassword, setNewDriverPassword ] = useState( "" );
    const [ newDriverName, setNewDriverName ] = useState( "" );
    const [ newDriverAvatar, setNewDriverAvatar ] = useState( "" );
    const [ newDriverBirthday, setNewDriverBirthday ] = useState( "" );
    const [ newDriverGender, setNewDriverGender ] = useState( "" );
    const [ newDriverCity, setNewDriverCity ] = useState( "" );
    const [ newDriverCountry, setNewDriverCountry ] = useState( "" );
    const [ isAdding, setIsAdding ] = useState( false );

    useEffect( () => {
        fetchDrivers();
    }, [] );

    const fetchDrivers = async () => {
        setLoading( true );
        try {
            const [allUsers, alertsData, appealsData] = await Promise.all([
                getUsers(),
                listAlerts(100),
                listAppealsAdmin()
            ]);
            const driverUsers = allUsers.filter( u => u.role === "driver" );
            setDrivers( driverUsers );
            setAllAlerts( alertsData );
            setAllAppeals( appealsData );

            setSelectedDriver( prev => {
                if ( !prev ) return null;
                return driverUsers.find( d => d.id === prev.id ) || prev;
            } );
        } catch ( err ) {
            console.error( "Failed to fetch drivers data", err );
        } finally {
            setLoading( false );
        }
    };

    const handleAddDriver = async ( e: React.FormEvent ) => {
        e.preventDefault();
        if ( !newDriverEmail ) return;
        setIsAdding( true );
        try {
            await createUser( {
                email: newDriverEmail,
                password: newDriverPassword || undefined,
                name: newDriverName || undefined,
                avatar_image_url: newDriverAvatar || undefined,
                birthday: newDriverBirthday || undefined,
                gender: newDriverGender || undefined,
                address__city: newDriverCity || undefined,
                address__country: newDriverCountry || undefined
            } );
            setIsAddModalOpen( false );
            setNewDriverEmail( "" );
            setNewDriverPassword( "" );
            setNewDriverName( "" );
            setNewDriverAvatar( "" );
            setNewDriverBirthday( "" );
            setNewDriverGender( "" );
            setNewDriverCity( "" );
            setNewDriverCountry( "" );
            fetchDrivers();
        } catch ( err ) {
            console.error( "Failed to add driver", err );
            alert( "Failed to add driver. Please check inputs." );
        } finally {
            setIsAdding( false );
        }
    };

    const filteredDrivers = drivers.filter( d =>
        ( d.name || "" ).toLowerCase().includes( searchTerm.toLowerCase() ) ||
        ( d.email || "" ).toLowerCase().includes( searchTerm.toLowerCase() )
    );

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest relative">
            <div className="flex items-center justify-between px-8 py-6 border-b border-surface-container-high bg-surface-container-lowest/80 backdrop-blur-xl sticky top-0 z-20 gap-4">
                <div className="flex flex-col gap-1">
                    <h1 className="text-2xl font-bold tracking-tight text-primary">{t("drivers.title")}</h1>
                    <p className="text-sm text-secondary">{t("drivers.subtitle")}</p>
                </div>
                
                <div className="flex items-center gap-4 flex-1 max-w-md ml-auto">
                    <div className="relative w-full">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
                        <input
                            type="text"
                            placeholder={t("common.search")}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full bg-surface-container rounded-lg pl-9 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary outline-none border border-outline-variant/10"
                        />
                    </div>
                    <button
                        onClick={ () => setIsAddModalOpen( true ) }
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 transition-opacity shrink-0 cursor-pointer"
                    >
                        <Plus className="w-5 h-5" /> {t("drivers.addDriver")}
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Driver List */ }
                <div className="w-1/3 border-r border-surface-container-high overflow-y-auto bg-surface-container-lowest/50">
                    { loading ? (
                        <LoadingRadar message={t("drivers.loadingDrivers")} minHeight="min-h-[400px]" />
                    ) : filteredDrivers.length === 0 ? (
                        <div className="p-8 text-center text-secondary">{t("drivers.noDrivers")}</div>
                    ) : (
                        <div className="flex flex-col divide-y divide-surface-container-high">
                            { filteredDrivers.map( driver => {
                                const score = calculateSafetyScore(driver.id, allAlerts, allAppeals);
                                const scoreInfo = getSafetyScoreLabel(score, language);
                                return (
                                    <button
                                        key={ driver.id }
                                        onClick={ () => setSelectedDriver( driver ) }
                                        className={ `flex items-start gap-4 py-5 px-4 text-left transition-colors relative ${ selectedDriver?.id === driver.id
                                            ? "bg-primary/10 border-l-4 border-primary"
                                            : "hover:bg-surface-container-low border-l-4 border-transparent"
                                            }` }
                                    >
                                        <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center shrink-0 overflow-hidden">
                                            { driver.avatar_image_url ? (
                                                <img src={ driver.avatar_image_url } alt={ driver.name || "Avatar" } className="w-full h-full object-cover" />
                                            ) : (
                                                <Users className="w-5 h-5 text-secondary" />
                                            ) }
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex justify-between items-start gap-2">
                                                <h3 className="font-bold text-on-surface truncate">{ driver.name || driver.email }</h3>
                                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md tracking-wider shrink-0 ${scoreInfo.colorClass}`}>
                                                    {score}
                                                </span>
                                            </div>
                                            <p className="text-sm text-secondary truncate">{ driver.email }</p>
                                            { driver.fingerprint_id ? (
                                                <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600">
                                                    <Fingerprint className="w-3 h-3" /> Enrolled
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded text-xs font-medium bg-error/10 text-error">
                                                    <Fingerprint className="w-3 h-3" /> Not Enrolled
                                                </span>
                                            ) }
                                        </div>
                                    </button>
                                );
                            } ) }
                        </div>
                    ) }
                </div>

                {/* Driver Details */ }
                <div className="flex-1 overflow-y-auto p-8">
                    { selectedDriver ? (
                        <DriverDetails driver={ selectedDriver } onUpdate={ fetchDrivers } allAlerts={ allAlerts } allAppeals={ allAppeals } />
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-secondary">
                            <Users className="w-16 h-16 mb-4 opacity-20" />
                            <p>Select a driver from the list to view details</p>
                        </div>
                    ) }
                </div>
            </div>

            {/* Add Driver Modal */ }
            { isAddModalOpen && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
                        <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
                            <h2 className="text-xl font-bold">Add New Driver</h2>
                            <button onClick={ () => setIsAddModalOpen( false ) } className="p-2 hover:bg-surface-container-low rounded-full">
                                <X className="w-5 h-5 text-secondary" />
                            </button>
                        </div>
                        <form onSubmit={ handleAddDriver } className="p-6 flex flex-col gap-6 overflow-y-auto">
                            <div className="flex flex-col md:flex-row gap-6">
                                <div className="w-full md:w-48 shrink-0 flex flex-col">
                                    <ImageUploader
                                        label="Avatar Image"
                                        currentUrl={ newDriverAvatar }
                                        onUploadSuccess={ ( url ) => setNewDriverAvatar( url ) }
                                    />
                                </div>

                                <div className="flex-1 flex flex-col gap-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">Email Address *</label>
                                            <input
                                                type="email"
                                                required
                                                value={ newDriverEmail }
                                                onChange={ e => setNewDriverEmail( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="driver@example.com"
                                            />
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">Password *</label>
                                            <input
                                                type="password"
                                                required
                                                minLength={ 8 }
                                                value={ newDriverPassword }
                                                onChange={ e => setNewDriverPassword( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="Min 8 characters"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">Full Name</label>
                                            <input
                                                type="text"
                                                value={ newDriverName }
                                                onChange={ e => setNewDriverName( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="John Doe"
                                            />
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">Date of Birth</label>
                                            <input
                                                type="date"
                                                value={ newDriverBirthday }
                                                onChange={ e => setNewDriverBirthday( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">Gender</label>
                                            <select
                                                value={ newDriverGender }
                                                onChange={ e => setNewDriverGender( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                            >
                                                <option value="">Select Gender</option>
                                                <option value="male">Male</option>
                                                <option value="female">Female</option>
                                                <option value="other">Other</option>
                                            </select>
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">City</label>
                                            <input
                                                type="text"
                                                value={ newDriverCity }
                                                onChange={ e => setNewDriverCity( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="Da Nang"
                                            />
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">Country</label>
                                            <input
                                                type="text"
                                                value={ newDriverCountry }
                                                onChange={ e => setNewDriverCountry( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="Vietnam"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-surface-container-high">
                                <button
                                    type="button"
                                    onClick={ () => setIsAddModalOpen( false ) }
                                    className="px-4 py-2 rounded-lg font-bold text-secondary hover:bg-surface-container-high"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={ isAdding || !newDriverEmail }
                                    className="px-4 py-2 rounded-lg font-bold bg-primary text-on-primary hover:opacity-90 disabled:opacity-50"
                                >
                                    { isAdding ? "Adding..." : "Add Driver" }
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            ) }
        </div>
    );
}

function calculateDuration(startStr: string, endStr?: string | null): string {
    const start = new Date(startStr);
    const end = endStr ? new Date(endStr) : new Date();
    const diffMs = end.getTime() - start.getTime();
    if (diffMs < 0) return "0m";
    
    const diffMins = Math.floor(diffMs / 60000);
    const hrs = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    
    if (hrs > 0) {
        return `${hrs}h ${mins}m`;
    }
    return `${mins}m`;
}

function DriverDetails ( { driver, onUpdate, allAlerts, allAppeals }: { driver: User, onUpdate: () => void, allAlerts: Alert[], allAppeals: Appeal[] } ) {
    const { t, language } = useLanguage();
    const [ sessions, setSessions ] = useState<DrivingSession[]>( [] );
    const [ alerts, setAlerts ] = useState<Alert[]>( [] );
    const [ loadingHistory, setLoadingHistory ] = useState( false );
    const navigate = useNavigate();

    const score = calculateSafetyScore(driver.id, allAlerts, allAppeals);
    const scoreInfo = getSafetyScoreLabel(score, language);

    const [ isScanning, setIsScanning ] = useState( false );
    const [ scanError, setScanError ] = useState<string | null>( null );

    const [ isEditModalOpen, setIsEditModalOpen ] = useState( false );
    const [ editName, setEditName ] = useState( "" );
    const [ editAvatar, setEditAvatar ] = useState( "" );
    const [ editBirthday, setEditBirthday ] = useState( "" );
    const [ editGender, setEditGender ] = useState( "" );
    const [ editCity, setEditCity ] = useState( "" );
    const [ editCountry, setEditCountry ] = useState( "" );
    const [ isSavingProfile, setIsSavingProfile ] = useState( false );

    const fetchHistory = useCallback( async () => {
        setLoadingHistory( true );
        try {
            const [ sessionsData, alertsData ] = await Promise.all( [
                getDrivingSessions( driver.id ),
                listAlerts( 50, driver.id )
            ] );
            setSessions( sessionsData );
            setAlerts( alertsData );
        } catch ( err ) {
            console.error( "Failed to fetch driver history", err );
        } finally {
            setLoadingHistory( false );
        }
    }, [ driver.id ] );

    useEffect( () => {
        setIsScanning( false );
        setScanError( null );

        setEditName( driver.name || "" );
        setEditAvatar( driver.avatar_image_url || "" );
        setEditBirthday( driver.birthday || "" );
        setEditGender( driver.gender || "" );
        setEditCity( driver.address__city || "" );
        setEditCountry( driver.address__country || "" );

        fetchHistory();
    }, [ driver, fetchHistory ] );

    useEffect( () => {
        const WS_BASE = env.apiBaseUrl.replace(/^http/, "ws") + "/ws";
        const wsUrl = `${WS_BASE}/frontend`;
        console.log("Connecting to WebSocket in DriverDetails:", wsUrl);
        
        let ws: WebSocket | null = null;
        let pingInterval: any = null;

        try {
            ws = new WebSocket( wsUrl );

            ws.onopen = () => {
                console.log("WebSocket connected successfully in DriverDetails");
                pingInterval = setInterval( () => {
                    if ( ws?.readyState === WebSocket.OPEN ) {
                        ws.send( JSON.stringify( { type: "ping" } ) );
                    }
                }, 10000 );
            };

            ws.onmessage = ( evt ) => {
                try {
                    const msg = JSON.parse( evt.data );
                    if ( msg.type === "fingerprint_updated" && msg.data?.user_id === driver.id ) {
                        console.log("Fingerprint updated via WebSocket broadcast:", msg.data);
                        setIsScanning( false );
                        onUpdate();
                    } else if ( msg.type === "driving_session_started" && msg.data?.driver_id === driver.id ) {
                        console.log("Driving session started via WS:", msg.data);
                        fetchHistory();
                        onUpdate();
                    } else if ( msg.type === "driving_session_ended" && msg.data?.driver_id === driver.id ) {
                        console.log("Driving session ended via WS:", msg.data);
                        fetchHistory();
                        onUpdate();
                    }
                } catch ( err ) {
                    console.error("Error parsing WebSocket message:", err);
                }
            };

            ws.onerror = ( err ) => {
                console.error("WebSocket error in DriverDetails:", err);
                if ( isScanning ) {
                    setScanError("WebSocket connection lost. Please try again.");
                }
            };

            ws.onclose = () => {
                console.log("WebSocket connection closed in DriverDetails");
                if ( pingInterval ) clearInterval( pingInterval );
            };
        } catch ( e ) {
            console.error("Failed to establish WebSocket connection:", e);
            if ( isScanning ) {
                setScanError("Failed to establish live WebSocket connection.");
            }
        }

        return () => {
            if ( ws ) {
                if ( ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING ) {
                    ws.close();
                }
            }
            if ( pingInterval ) clearInterval( pingInterval );
        };
    }, [ driver.id, onUpdate, isScanning, fetchHistory ] );

    const handleTriggerEnroll = async () => {
        setIsScanning( true );
        setScanError( null );
        try {
            await enrollFingerprint( driver.id );
        } catch ( err ) {
            console.error( "Failed to trigger fingerprint enrollment", err );
            setScanError( "Failed to trigger enrollment command. Make sure Backend and Simulator/Device are running." );
            setIsScanning( false );
        }
    };

    const handleSaveProfile = async ( e: React.FormEvent ) => {
        e.preventDefault();
        setIsSavingProfile( true );
        try {
            const { updateUser } = await import( "@/api/users" );
            await updateUser( driver.id, {
                name: editName || null,
                avatar_image_url: editAvatar || null,
                birthday: editBirthday || null,
                gender: editGender || null,
                address__city: editCity || null,
                address__country: editCountry || null,
            } );
            setIsEditModalOpen( false );
            onUpdate();
        } catch ( err ) {
            console.error( "Failed to update profile", err );
            alert( "Failed to update profile." );
        } finally {
            setIsSavingProfile( false );
        }
    };

    return (
        <div className="max-w-4xl mx-auto flex flex-col gap-4 relative">
            {/* Profile Header */ }
            <div className="bg-surface-container rounded-2xl p-4 flex items-start gap-4 relative">
                <button
                    onClick={ () => setIsEditModalOpen( true ) }
                    className="absolute top-4 right-4 p-2 rounded-lg bg-surface-container-high text-secondary hover:text-primary transition-colors cursor-pointer"
                    title={language === "en" ? "Edit Profile" : "Chỉnh sửa hồ sơ"}
                >
                    <Edit2 className="w-3.5 h-3.5" />
                </button>
                <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center shrink-0 overflow-hidden">
                    { driver.avatar_image_url ? (
                        <img src={ driver.avatar_image_url } alt={ driver.name || "Avatar" } className="w-full h-full object-cover" />
                    ) : (
                        <Users className="w-7 h-7 text-primary" />
                    ) }
                </div>
                <div className="flex-1 pr-12">
                    <h2 className="text-lg font-bold text-on-surface">{ driver.name || "Unknown Name" }</h2>
                    <p className="text-xs text-secondary mb-2">{ driver.email }</p>
 
                    {/* Safety Score progress bar */}
                    <div className="mb-4 max-w-md">
                        <div className="flex items-center justify-between text-xs font-semibold mb-1">
                            <span className="text-secondary">{t("drivers.safetyScore")}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${scoreInfo.colorClass}`}>
                                {score}/100 — {scoreInfo.label}
                            </span>
                        </div>
                        <div className="w-full bg-surface-container-high rounded-full h-2 overflow-hidden border border-outline-variant/10">
                            <div 
                                className={`h-full rounded-full transition-all duration-500 ${
                                    score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : "bg-error"
                                }`} 
                                style={{ width: `${score}%` }} 
                            />
                        </div>
                    </div>
 
                    <div className="flex flex-col gap-2 mt-2">
                        <h4 className="text-[10px] font-black text-secondary uppercase tracking-wider">
                            {language === "en" ? "Fingerprint Device Integration" : "Tích hợp thiết bị vân tay"}
                        </h4>
                        { isScanning ? (
                            <div className="bg-surface-container-high border border-primary/20 rounded-xl p-3 flex flex-col gap-2 max-w-md">
                                <div className="flex items-start gap-2.5">
                                    <div className="p-1.5 bg-primary/10 text-primary rounded-lg shrink-0 animate-pulse">
                                        <Fingerprint className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-1.5">
                                            <span className="font-bold text-xs text-on-surface">
                                                {language === "en" ? "Scanning..." : "Đang quét..."}
                                            </span>
                                            <RefreshCw className="w-3 h-3 text-primary animate-spin" />
                                        </div>
                                        <p className="text-[10px] text-secondary mt-0.5 leading-snug">
                                            {t("drivers.scanInstruction")}
                                        </p>
                                    </div>
                                </div>
                                { scanError && (
                                    <div className="text-[10px] text-red-500 font-medium bg-red-500/5 p-1.5 rounded border border-red-500/10">
                                        { scanError }
                                    </div>
                                ) }
                                <button
                                    onClick={ () => setIsScanning( false ) }
                                    className="self-end px-2 py-0.5 text-[10px] font-bold text-red-500 border border-red-500/30 hover:bg-red-500/10 rounded-md transition-colors cursor-pointer"
                                >
                                    {t("common.cancel")}
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2">
                                { driver.fingerprint_id ? (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs bg-emerald-500/10 text-emerald-600 font-semibold" title={ driver.fingerprint_id }>
                                        <Fingerprint className="w-3.5 h-3.5" /> {t("drivers.enrolled")}
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs bg-surface-container-highest text-secondary font-medium">
                                        <Fingerprint className="w-3.5 h-3.5" /> {language === "en" ? "Not Set" : "Chưa thiết lập"}
                                    </span>
                                ) }
                                <button
                                    onClick={ handleTriggerEnroll }
                                    className="flex items-center gap-1 px-2.5 py-1 bg-primary/10 hover:bg-primary/20 text-primary text-[10px] font-bold rounded-md transition-colors cursor-pointer"
                                >
                                    { driver.fingerprint_id ? (language === "en" ? "Re-scan / Re-enroll" : "Quét lại / Đăng ký lại") : t("drivers.registerWithSim") }
                                </button>
                            </div>
                        ) }
                    </div>
                </div>
            </div>
 
            <div className="grid grid-cols-2 gap-4">
                {/* Driving Sessions */ }
                <div className="flex flex-col gap-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-primary" /> {t("drivers.timekeepingHistory")}
                    </h3>
                    <div className="bg-surface-container rounded-xl overflow-hidden">
                        { loadingHistory ? (
                            <LoadingRadar message={t("common.loading")} minHeight="min-h-[200px]" />
                        ) : sessions.length === 0 ? (
                            <div className="p-4 text-center text-secondary text-xs">{t("drivers.noSessions")}</div>
                        ) : (
                            <div className="flex flex-col divide-y divide-surface-container-high max-h-[380px] overflow-y-auto">
                                { sessions.map( session => {
                                    const isActive = session.status === "ACTIVE";
                                    return (
                                        <div key={ session.id } className={`p-2.5 flex flex-col gap-1 transition-colors ${isActive ? "bg-emerald-500/5" : ""}`}>
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-bold flex items-center gap-1">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                                                    {language === "en" ? "Clock In" : "Giờ vào"}: { new Date( session.started_at ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } ) }
                                                </span>
                                                { isActive ? (
                                                    <span className="text-[10px] font-black text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded animate-pulse">
                                                        {t("vehicles.currentlyDriving")}
                                                    </span>
                                                ) : (
                                                    <span className="text-[10px] font-bold text-secondary bg-surface-container-high px-1.5 py-0.5 rounded">
                                                        {t("vehicles.completed")}
                                                    </span>
                                                ) }
                                            </div>
                                            
                                            <div className="flex items-center justify-between text-[11px] text-secondary pl-2.5">
                                                <span>
                                                    { isActive ? (
                                                        language === "en" ? "Active shift in progress" : "Ca làm việc đang hoạt động"
                                                    ) : (
                                                        `${language === "en" ? "Clock Out" : "Giờ ra"}: ${new Date( session.ended_at || "" ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } )}`
                                                    ) }
                                                </span>
                                                <span className={`font-semibold ${isActive ? "text-emerald-600 font-bold" : ""}`}>
                                                    {language === "en" ? "Duration" : "Thời lượng"}: { calculateDuration( session.started_at, session.ended_at ) }
                                                </span>
                                            </div>
                                        </div>
                                    );
                                } ) }
                            </div>
                        ) }
                    </div>
                </div>
 
                {/* Violations */ }
                <div className="flex flex-col gap-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-error" /> {language === "en" ? "Violation History" : "Lịch sử vi phạm"}
                    </h3>
                    <div className="bg-surface-container rounded-xl overflow-hidden">
                        { loadingHistory ? (
                            <LoadingRadar message={t("common.loading")} minHeight="min-h-[200px]" />
                        ) : alerts.length === 0 ? (
                            <div className="p-4 text-center text-secondary text-xs">{language === "en" ? "No violations found." : "Không có vi phạm nào."}</div>
                        ) : (
                            <div className="flex flex-col divide-y divide-surface-container-high max-h-[380px] overflow-y-auto">
                                { alerts.map( alert => (
                                    <div key={ alert.id } className="p-2.5 flex flex-col gap-1 hover:bg-surface-container-low transition-colors group">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-xs font-bold text-error">{ alert.alertType.replace( "_", " " ) }</span>
                                                    <span className="text-[9px] font-bold text-secondary bg-surface-container-highest px-1 py-0.5 rounded uppercase">{ alert.status }</span>
                                                </div>
                                                <span className="text-[10px] text-secondary">{ new Date( alert.createdAt ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } ) }</span>
                                            </div>
                                            <button
                                                onClick={ () => navigate( `/alerts/${ alert.id }` ) }
                                                className="opacity-0 group-hover:opacity-100 p-1 bg-primary/10 text-primary rounded-md transition-all hover:bg-primary/20 shrink-0 cursor-pointer"
                                                title={language === "en" ? "View Incident Details" : "Xem chi tiết sự cố"}
                                            >
                                                <ExternalLink className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                        <p className="text-xs text-on-surface line-clamp-2 leading-relaxed">{ alert.message }</p>
                                    </div>
                                ) ) }
                            </div>
                        ) }
                    </div>
                </div>
            </div>

            {/* Edit Profile Modal */ }
            { isEditModalOpen && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
                        <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
                            <h2 className="text-xl font-bold">{language === "en" ? "Edit Driver Profile" : "Sửa hồ sơ tài xế"}</h2>
                            <button onClick={ () => setIsEditModalOpen( false ) } className="p-2 hover:bg-surface-container-low rounded-full cursor-pointer">
                                <X className="w-5 h-5 text-secondary" />
                            </button>
                        </div>
                        <form onSubmit={ handleSaveProfile } className="p-6 flex flex-col gap-6 overflow-y-auto">
                            <div className="flex flex-col md:flex-row gap-6">
                                <div className="w-full md:w-48 shrink-0 flex flex-col">
                                    <ImageUploader
                                        label={t("drivers.avatar")}
                                        currentUrl={ editAvatar }
                                        onUploadSuccess={ ( url ) => setEditAvatar( url ) }
                                    />
                                </div>
                                <div className="flex-1 flex flex-col gap-4">
                                    <div className="grid grid-cols-1 gap-4">
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">{t("drivers.fullName")}</label>
                                            <input
                                                type="text"
                                                value={ editName }
                                                onChange={ e => setEditName( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="John Doe"
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">{t("drivers.dob")}</label>
                                            <input
                                                type="date"
                                                value={ editBirthday }
                                                onChange={ e => setEditBirthday( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                            />
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">{t("drivers.gender")}</label>
                                            <select
                                                value={ editGender }
                                                onChange={ e => setEditGender( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                            >
                                                <option value="">{t("drivers.selectGender")}</option>
                                                <option value="male">{t("drivers.male")}</option>
                                                <option value="female">{t("drivers.female")}</option>
                                                <option value="other">{t("drivers.other")}</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="flex flex-col gap-2">
                                            <label className="text-sm font-bold text-secondary">{t("drivers.city")}</label>
                                            <input
                                                type="text"
                                                value={ editCity }
                                                onChange={ e => setEditCity( e.target.value ) }
                                                className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                                                placeholder="Da Nang"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 mt-2 pt-4 border-t border-surface-container-high">
                                <button
                                    type="button"
                                    onClick={ () => setIsEditModalOpen( false ) }
                                    className="px-4 py-2 rounded-lg font-bold text-secondary hover:bg-surface-container-high cursor-pointer"
                                >
                                    {t("common.cancel")}
                                </button>
                                <button
                                    type="submit"
                                    disabled={ isSavingProfile }
                                    className="px-4 py-2 rounded-lg font-bold bg-primary text-on-primary hover:opacity-90 disabled:opacity-50 cursor-pointer"
                                >
                                    { isSavingProfile ? (language === "en" ? "Saving..." : "Đang lưu...") : t("common.save") }
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            ) }
        </div>
    );
}
