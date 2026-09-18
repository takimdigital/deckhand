import { Card } from "@/components/ui/card";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export function PricingCard({ tier }: { tier: string }) {
  return (
    <motion.div className={cn("rounded-xl border p-6", "bg-card")}>
      <Card>{tier}</Card>
    </motion.div>
  );
}
