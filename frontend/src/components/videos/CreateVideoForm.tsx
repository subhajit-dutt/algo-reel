"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useCreateJob } from "@/hooks/useCreateJob";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { DurationTarget, Renderer } from "@/types/api";

const schema = z.object({
  prompt: z.string().min(1, "prompt required").max(2000, "max 2000 characters"),
  renderer: z.enum(["manim", "ai_image"]),
  duration_target: z.enum(["30", "60", "180"]),
  voice: z.string().min(1, "voice required").max(64, "max 64 characters"),
});

type FormValues = z.infer<typeof schema>;

const RENDERER_OPTIONS: { value: Renderer; label: string; tag: string }[] = [
  { value: "manim", label: "Manim", tag: "3blue1brown-style" },
  { value: "ai_image", label: "AI Image", tag: "flux + ken-burns" },
];

const DURATION_OPTIONS: { value: `${DurationTarget}`; label: string }[] = [
  { value: "30", label: "30 seconds" },
  { value: "60", label: "60 seconds" },
  { value: "180", label: "3 minutes" },
];

export function CreateVideoForm() {
  const router = useRouter();
  const mutation = useCreateJob();
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { renderer: "manim", duration_target: "60", voice: "alloy", prompt: "" },
  });

  const renderer = watch("renderer");
  const duration = watch("duration_target");
  const prompt = watch("prompt") ?? "";

  const onSubmit = handleSubmit(async (values) => {
    try {
      const job = await mutation.mutateAsync({
        prompt: values.prompt,
        renderer: values.renderer,
        duration_target: Number(values.duration_target) as DurationTarget,
        voice: values.voice,
      });
      toast.success(`job #${job.id} queued`);
      router.push(`/videos/${job.id}/`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "failed to create job";
      toast.error(msg);
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between">
          <Label htmlFor="prompt">Prompt</Label>
          <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
            {prompt.length}/2000
          </span>
        </div>
        <Textarea
          id="prompt"
          rows={5}
          placeholder="Explain merge sort in 60 seconds. Audience: CS undergrads. Use a clear visual of array partitioning."
          {...register("prompt")}
        />
        {errors.prompt && (
          <p className="font-mono text-[11px] text-destructive">{errors.prompt.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="renderer">Renderer</Label>
          <Select
            value={renderer}
            onValueChange={(v) => setValue("renderer", v as Renderer, { shouldValidate: true })}
          >
            <SelectTrigger id="renderer">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RENDERER_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  <div className="flex items-baseline gap-2">
                    <span>{opt.label}</span>
                    <span className="text-[10px] text-muted-foreground">{opt.tag}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="duration">Duration</Label>
          <Select
            value={duration}
            onValueChange={(v) =>
              setValue("duration_target", v as `${DurationTarget}`, { shouldValidate: true })
            }
          >
            <SelectTrigger id="duration">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DURATION_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="voice">Voice</Label>
          <Input id="voice" placeholder="alloy" {...register("voice")} />
          {errors.voice && (
            <p className="font-mono text-[11px] text-destructive">{errors.voice.message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 pt-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
          {renderer === "manim" ? "cpu-bound · ~30–120s/scene" : "image-based · ~5s/scene"}
        </span>
        <Button type="submit" disabled={isSubmitting} className={cn("min-w-[160px]")}>
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" /> queueing…
            </>
          ) : (
            <>
              <Sparkles className="size-4" /> generate video
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
