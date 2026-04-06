/**
 * CONFIT CARE Landing Page
 * Information about the donation system
 */

import Link from 'next/link';
import { Button } from '@/components/ui/button';

export const metadata = {
  title: 'CONFIT CARE — Fashion for Everyone',
  description: 'Create donation campaigns to help those in need shop for clothing with dignity.',
};

export default function CareLandingPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="py-20 bg-gradient-to-br from-[var(--color-gold-50)] to-white">
        <div className="container text-center">
          <span className="inline-block px-4 py-1 rounded-full bg-[var(--color-gold-100)] text-[var(--color-gold-500)] text-sm font-medium mb-6">
            Making Fashion Accessible
          </span>
          <h1 className="text-4xl md:text-5xl font-display font-semibold mb-6">
            CONFIT CARE
          </h1>
          <p className="text-xl text-[var(--color-gray-600)] max-w-2xl mx-auto mb-10">
            Create donation campaigns to help those in need shop for clothing with dignity.
            Every contribution makes a difference.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/care/dashboard">
              <Button size="lg">Start a Campaign</Button>
            </Link>
            <Link href="#how-it-works">
              <Button variant="outline" size="lg">
                Learn How It Works
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 bg-white">
        <div className="container">
          <h2 className="text-3xl font-display font-semibold text-center mb-12">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <StepCard
              number={1}
              title="Create a Campaign"
              description="Set up a donation campaign with a target amount and timeline. Add beneficiaries who will receive shopping vouchers."
            />
            <StepCard
              number={2}
              title="Fund the Campaign"
              description="Add funds to your campaign via secure payment. The money goes into vouchers for your beneficiaries."
            />
            <StepCard
              number={3}
              title="Beneficiaries Shop"
              description="Beneficiaries receive vouchers they can use to shop for clothing on CONFIT, maintaining their dignity and choice."
            />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-[var(--color-beige-50)]">
        <div className="container">
          <h2 className="text-3xl font-display font-semibold text-center mb-12">
            Features for Donors
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <FeatureCard
              title="Campaign Dashboard"
              description="Track your campaigns, donations, and impact in real-time."
            />
            <FeatureCard
              title="Beneficiary Management"
              description="Add and manage beneficiaries with individual budget caps."
            />
            <FeatureCard
              title="Voucher System"
              description="Generate unique voucher codes that beneficiaries can use at checkout."
            />
            <FeatureCard
              title="Impact Tracking"
              description="See how your donations are being used and the difference you're making."
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-[var(--color-gold-400)] text-white">
        <div className="container text-center">
          <h2 className="text-3xl font-display font-semibold mb-6">
            Ready to Make a Difference?
          </h2>
          <p className="text-xl opacity-90 max-w-2xl mx-auto mb-10">
            Start a CONFIT CARE campaign today and help someone shop for clothing with dignity.
          </p>
          <Link href="/care/dashboard">
            <Button
              size="lg"
              className="bg-white text-[var(--color-gold-500)] hover:bg-[var(--color-beige-100)]"
            >
              Get Started
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}

function StepCard({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: string;
}) {
  return (
    <div className="text-center p-6">
      <div className="w-12 h-12 rounded-full bg-[var(--color-gold-400)] text-white flex items-center justify-center text-xl font-bold mx-auto mb-4">
        {number}
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-[var(--color-gray-600)]">{description}</p>
    </div>
  );
}

function FeatureCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl border border-[var(--color-beige-200)] bg-white">
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-[var(--color-gray-600)]">{description}</p>
    </div>
  );
}
