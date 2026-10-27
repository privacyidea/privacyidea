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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, Router } from "@angular/router";
import { UserNewResolverComponent } from "@components/user/user-new-resolver/user-new-resolver.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { MachineResolverService } from "@services/machine-resolver/machine-resolver.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockDialogService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { of } from "rxjs";
import { MachineResolverDetailsComponent } from "./machine-resolver-details.component";

(globalThis as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver = class {
  disconnect = jest.fn();
  observe = jest.fn();
  unobserve = jest.fn();
  takeRecords = jest.fn().mockReturnValue([]);
} as unknown as typeof IntersectionObserver;

/**
 * The machine resolver and the user resolver form validate the resolver name with the same schema
 * (`identifierName` with `RESOLVER_RESERVED_NAMES`), so both accept and reject the same names.
 */
describe("resolver name schema shared by the machine resolver and the user resolver form", () => {
  let machineForm: MachineResolverDetailsComponent["nameForm"];
  let machineModel: MachineResolverDetailsComponent["nameModel"];
  let userForm: UserNewResolverComponent["resolverNameForm"];
  let userModel: UserNewResolverComponent["resolverNameModel"];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverDetailsComponent, UserNewResolverComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ActivatedRoute, useValue: { paramMap: of({ get: () => "" }) } },
        { provide: Router, useValue: { navigate: jest.fn(), navigateByUrl: jest.fn(), events: of(), url: "" } }
      ]
    }).compileComponents();

    const machine = TestBed.createComponent(MachineResolverDetailsComponent).componentInstance;
    const user = TestBed.createComponent(UserNewResolverComponent).componentInstance;
    machineForm = machine.nameForm;
    machineModel = machine.nameModel;
    userForm = user.resolverNameForm;
    userModel = user.resolverNameModel;
  });

  const outcome = (name: string) => {
    machineModel.set({ resolvername: name });
    userModel.set({ resolverName: name });
    return {
      machine: {
        valid: machineForm().valid(),
        kinds: machineForm
          .resolvername()
          .errors()
          .map((e) => e.kind)
      },
      user: {
        valid: userForm().valid(),
        kinds: userForm
          .resolverName()
          .errors()
          .map((e) => e.kind)
      }
    };
  };

  it.each(["resolver1", "a", "my.resolver", "my_resolver", "my-resolver", "A.b_c-9", "test_request", "testing", "..."])(
    "accepts %p in both forms",
    (name) => {
      const { machine, user } = outcome(name);
      expect(machine).toEqual({ valid: true, kinds: [] });
      expect(user).toEqual(machine);
    }
  );

  it.each([
    ["", ["required"]],
    ["has space", ["pattern"]],
    [" leading", ["pattern"]],
    ["trailing ", ["pattern"]],
    ["ümlaut", ["pattern"]],
    ["slash/name", ["pattern"]],
    ["a:b", ["pattern"]],
    ["test", ["reservedName"]],
    [".", ["reservedName"]],
    ["..", ["reservedName"]]
  ])("rejects %p with the same error kinds in both forms", (name, kinds) => {
    const { machine, user } = outcome(name);
    expect(machine).toEqual({ valid: false, kinds });
    expect(user).toEqual(machine);
  });
});
