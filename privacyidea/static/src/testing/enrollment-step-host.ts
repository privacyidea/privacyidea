/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { Provider, signal, WritableSignal } from "@angular/core";
import type { EnrollmentFirstStep, EnrollmentFlow } from "@components/token/token-enrollment/enrollment-flow";
import { ENROLLMENT_STEP_HOST, EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { TokenEnrollmentDialogData } from "@services/token/token.service";
import { NEVER } from "rxjs";

export interface MockEnrollmentStepHost {
  flow: {
    dialogData: WritableSignal<TokenEnrollmentDialogData | null>;
    finishStep: jest.Mock;
    close: jest.Mock;
    firstStep: EnrollmentFirstStep | null;
    reopened: boolean;
  };
  register: jest.Mock<void, [EnrollmentStep]>;
  provider: Provider;
}

// A stand-in for the enrollment dialog, so a step can be tested on its own with the given enrollment data.
export function mockEnrollmentStepHost(
  data: unknown,
  state: { firstStep?: EnrollmentFirstStep; reopened?: boolean } = {}
): MockEnrollmentStepHost {
  const flow = {
    dialogData: signal(data as TokenEnrollmentDialogData | null),
    finishStep: jest.fn(),
    close: jest.fn(),
    stepFinished: NEVER,
    firstStep: state.firstStep ?? null,
    reopened: state.reopened ?? false
  };
  const register = jest.fn<void, [EnrollmentStep]>();
  return {
    flow,
    register,
    provider: {
      provide: ENROLLMENT_STEP_HOST,
      useValue: { flow: flow as unknown as EnrollmentFlow, register }
    }
  };
}
