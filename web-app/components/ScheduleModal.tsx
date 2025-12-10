/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { format, addMinutes, parseISO, isWithinInterval } from 'date-fns';
import { Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import {
    Dialog, DialogContent, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import {
    Form, FormControl, FormField, FormItem, FormLabel, FormMessage
} from "@/components/ui/form";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from '@/services/api';
import { SurgeryCase } from '@/components/types';

// Constants
const SPECIALTIES = [
    'Orthopedics', 'General', 'Cardiology', 'Urology', 'Thoracic',
    'Neurology', 'Otology', 'Vascular', 'Podiatry', 'Ophthalmology'
];

const OR_SUITES = ['OR-1', 'OR-2', 'OR-3', 'OR-4'];
const TIME_SLOTS = Array.from({ length: 11 }, (_, i) => 8 + i); // 8 AM to 6 PM

// Schema
const formSchema = z.object({
    patient_name: z.string().min(2, "Name is required"),
    service: z.string().min(1, "Service is required"),
    booked_time: z.coerce.number().min(1, "Time is required"),
    doctor_name: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface ScheduleModalProps {
    isOpen: boolean;
    onClose: () => void;
    selectedDate: Date;
    onSuccess: () => void;
    existingAndAllCases: SurgeryCase[];
    editCase: SurgeryCase | null;
}

export function ScheduleModal({ isOpen, onClose, selectedDate, onSuccess, existingAndAllCases, editCase }: ScheduleModalProps) {
    const [prediction, setPrediction] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedSlot, setSelectedSlot] = useState<{ or: string, hour: number } | null>(null);
    const [allDoctors, setAllDoctors] = useState<Record<string, string[]>>({});

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            patient_name: "",
            service: "",
            booked_time: 0,
            doctor_name: ""
        }
    });

    useEffect(() => {
        // Fetch doctors
        api.getDoctors().then(setAllDoctors).catch(console.error);
    }, []);

    useEffect(() => {
        if (isOpen) {
            if (editCase) {
                // Edit Mode
                form.reset({
                    patient_name: editCase.extendedProps.patient_name,
                    service: editCase.extendedProps.service,
                    booked_time: editCase.extendedProps.booked_time,
                    doctor_name: editCase.extendedProps.doctor_name || ""
                });
                setPrediction(editCase.extendedProps.actual_duration || null);

                // Set slot from existing date
                const start = new Date(editCase.start);
                setSelectedSlot({
                    or: editCase.extendedProps.or_suite,
                    hour: start.getHours()
                });
            } else {
                // Create Mode
                form.reset({
                    patient_name: "",
                    service: "",
                    booked_time: 0,
                    doctor_name: ""
                });
                setPrediction(null);
                setSelectedSlot(null);
            }
        }
    }, [isOpen, editCase, form]);

    const handlePredict = async () => {
        const values = form.getValues();
        if (!values.service || !values.booked_time) {
            toast.error("Please fill Service and Booked Time");
            return;
        }

        setIsLoading(true);
        try {
            const res = await api.getPrediction({
                date: selectedDate.toISOString(),
                service: values.service,
                booked_time: values.booked_time,
                patient_name: values.patient_name,
                or_suite: "TBD"
            });
            setPrediction(res.predicted_duration);
            toast.success(`Predicted Duration: ${res.predicted_duration} mins`);
        } catch (error) {
            toast.error("Prediction failed");
        } finally {
            setIsLoading(false);
        }
    };

    const isSlotAvailable = (or: string, hour: number, duration: number) => {
        const slotStart = new Date(selectedDate);
        slotStart.setHours(hour, 0, 0, 0);
        const slotEnd = addMinutes(slotStart, duration);

        return !existingAndAllCases.some(c => {
            if (editCase && c.id === editCase.id) return false; // Ignore self in edit
            if (c.extendedProps.or_suite !== or) return false;

            const cStart = new Date(c.start);
            const cEnd = c.end ? new Date(c.end) : addMinutes(cStart, c.extendedProps.actual_duration || 60);

            // Check overlap
            return (slotStart < cEnd && slotEnd > cStart);
        });
    };

    // Check doctor availability
    const getAvailableDoctors = () => {
        const service = form.watch('service');
        if (!service || !allDoctors[service]) return [];

        const doctors = allDoctors[service];

        if (!selectedSlot || !prediction) return doctors; // Return all if no slot selected yet

        // Filter doctors who are busy at the selected slot
        const slotStart = new Date(selectedDate);
        slotStart.setHours(selectedSlot.hour, 0, 0, 0);
        const slotEnd = addMinutes(slotStart, prediction);

        return doctors.filter(doc => {
            // Check if this doctor has any case that overlaps
            const isBusy = existingAndAllCases.some(c => {
                if (editCase && c.id === editCase.id) return false;
                if (c.extendedProps.doctor_name !== doc) return false;

                const cStart = new Date(c.start);
                const cEnd = c.end ? new Date(c.end) : addMinutes(cStart, c.extendedProps.actual_duration || 60);

                return (slotStart < cEnd && slotEnd > cStart);
            });
            return !isBusy;
        });
    };

    const availableDoctors = getAvailableDoctors();

    const onSubmit = async (values: z.infer<typeof formSchema>) => {
        if (!selectedSlot || !prediction) {
            toast.error("Please select a time slot after getting prediction.");
            return;
        }

        setIsLoading(true);
        const startTime = new Date(selectedDate);
        startTime.setHours(selectedSlot.hour, 0, 0, 0);
        const endTime = addMinutes(startTime, prediction);

        const payload = {
            date: selectedDate.toISOString(),
            service: values.service,
            booked_time: values.booked_time,
            patient_name: values.patient_name,
            or_suite: selectedSlot.or,
            duration: prediction,
            wheels_in: startTime.toISOString(),
            wheels_out: endTime.toISOString(),
            actual_duration: prediction,
            doctor_name: values.doctor_name
        };

        try {
            if (editCase) {
                await api.updateCase(editCase.id, payload);
                toast.success("Schedule Updated");
            } else {
                await api.createCase(payload);
                toast.success("Schedule Created");
            }
            onClose();
            onSuccess();
        } catch (error) {
            toast.error("Failed to save schedule");
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!editCase) return;
        // if (!confirm("Are you sure you want to delete this surgery?")) return;

        setIsLoading(true);
        try {
            await api.deleteCase(editCase.id);
            toast.success("Surgery Deleted");
            onClose();
            onSuccess();
        } catch (error) {
            toast.error("Failed to delete");
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{editCase ? "Edit Surgery" : "New Surgery Schedule"} - {format(selectedDate, 'MMM dd, yyyy')}</DialogTitle>
                </DialogHeader>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Left: Form */}
                    <div className="space-y-4">
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="patient_name"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Patient Name</FormLabel>
                                            <FormControl>
                                                <Input placeholder="John Doe" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="grid grid-cols-2 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="service"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Specialty</FormLabel>
                                                <Select onValueChange={async (val) => {
                                                    field.onChange(val);
                                                    form.setValue('doctor_name', ''); // Reset doctor on specialty change

                                                    // AI Suggestion for Time
                                                    try {
                                                        const dateStr = selectedDate.toISOString();
                                                        toast.info("Consulting AI Model...");
                                                        const res = await api.getAveragePrediction(val, dateStr);

                                                        if (res && res.predicted_duration) {
                                                            // Force update with validation
                                                            form.setValue('booked_time', res.predicted_duration, {
                                                                shouldValidate: true,
                                                                shouldDirty: true
                                                            });
                                                            toast.success(`AI Model Suggested: ${res.predicted_duration} mins`);
                                                        }
                                                    } catch (e) {
                                                        console.error("Auto-fill failed", e);
                                                        toast.error("Could not fetch suggested time");
                                                    }
                                                }} value={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Select..." />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        {SPECIALTIES.map(s => (
                                                            <SelectItem key={s} value={s}>{s}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="booked_time"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Est. Time (min)</FormLabel>
                                                <FormControl>
                                                    <Input type="number" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                <Button type="button" onClick={handlePredict} disabled={isLoading} className="w-full" variant="secondary">
                                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Get AI Suggestion
                                </Button>

                                {prediction && (
                                    <div className="p-3 bg-muted rounded-md text-sm text-center">
                                        AI Predicted Duration: <span className="font-bold">{prediction} mins</span>
                                    </div>
                                )}

                                {/* Doctor Selection - Only shown if Service is selected */}
                                {form.watch('service') && (
                                    <FormField
                                        control={form.control}
                                        name="doctor_name"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Surgeon (Available Only)</FormLabel>
                                                <Select onValueChange={field.onChange} value={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Select Doctor" />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        {availableDoctors.length > 0 ? (
                                                            availableDoctors.map(doc => (
                                                                <SelectItem key={doc} value={doc}>{doc}</SelectItem>
                                                            ))
                                                        ) : (
                                                            <SelectItem value="none" disabled>No Doctors Available</SelectItem>
                                                        )}
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                )}

                                <div className="flex gap-2 pt-2">
                                    <Button type="submit" disabled={isLoading || !selectedSlot} className="flex-1">
                                        {editCase ? "Update Schedule" : "Confirm Schedule"}
                                    </Button>
                                    {editCase && (
                                        <Button type="button" variant="destructive" onClick={handleDelete} disabled={isLoading}>
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                            </form>
                        </Form>
                    </div>

                    {/* Right: Slot Selection */}
                    <div className="border rounded-md p-4 h-[500px] overflow-y-auto">
                        <h3 className="font-semibold mb-4">Select OR Slot</h3>
                        {!prediction ? (
                            <div className="text-center text-muted-foreground py-10">
                                Get AI prediction to see availability.
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {OR_SUITES.map(or => (
                                    <div key={or}>
                                        <div className="text-sm font-medium mb-2 sticky top-0 bg-background z-10">{or}</div>
                                        <div className="grid grid-cols-4 gap-2">
                                            {TIME_SLOTS.map(hour => {
                                                const isAvail = isSlotAvailable(or, hour, prediction);
                                                const isSelected = selectedSlot?.or === or && selectedSlot?.hour === hour;

                                                return (
                                                    <button
                                                        key={hour}
                                                        type="button"
                                                        disabled={!isAvail}
                                                        onClick={() => setSelectedSlot({ or, hour })}
                                                        className={`
                                                            p-2 text-xs rounded border transition-colors
                                                            ${isSelected ? 'bg-primary text-primary-foreground border-primary' : ''}
                                                            ${!isAvail ? 'bg-muted text-muted-foreground cursor-not-allowed opacity-50' : 'hover:bg-accent'}
                                                        `}
                                                    >
                                                        {hour}:00
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
