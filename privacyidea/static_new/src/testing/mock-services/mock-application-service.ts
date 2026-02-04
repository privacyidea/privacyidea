/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { WritableSignal, signal } from "@angular/core";

type TestApplicationsShape = {
  ssh: { options: { sshkey: { service_id: { value: string[] } } } };
};

export class MockApplicationService {
  applications: WritableSignal<TestApplicationsShape> = signal({
    ssh: { options: { sshkey: { service_id: { value: ["svc-1", "svc-2"] } } } }
  });
}
