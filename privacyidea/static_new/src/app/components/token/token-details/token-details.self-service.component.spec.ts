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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, Router } from "@angular/router";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { MachineService } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import { ValidateService } from "@services/validate/validate.service";
import {
  MockAuditService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockMachineService,
  MockNotificationService,
  MockPendingChangesService,
  MockRealmService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService,
  MockValidateService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";
// NOTE: token-details.component must be loaded before the self-service component.
// token-details-info.component imports TIMESTAMP_INFO_KEYS from token-details.component;
// loading the info component first leaves the parent's @ViewChild(TokenDetailsInfoComponent)
// query with an undefined selector (circular import initialization order).
import { TokenDetailsComponent } from "./token-details.component";
import { TokenDetailsSelfServiceComponent } from "./token-details.self-service.component";

describe("TokenDetailsSelfServiceComponent", () => {
  let fixture: ComponentFixture<TokenDetailsSelfServiceComponent>;
  let component: TokenDetailsSelfServiceComponent;

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsSelfServiceComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: AuditService, useClass: MockAuditService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: UserService, useClass: MockUserService },
        { provide: MatDialog, useValue: { open: jest.fn() } },
        { provide: Router, useValue: { navigateByUrl: jest.fn().mockResolvedValue(true) } },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsSelfServiceComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal("Mock serial");
    component.tokenIsActive = signal(true);
    component.tokenIsRevoked = signal(false);
    component.infoData = signal([
      { keyMap: { key: "info", label: "Info" }, value: { key1: "value1" }, isEditing: signal(false) }
    ]);
    component.tokenDetailData = signal([
      { keyMap: { key: "container_serial", label: "Container" }, value: "container1", isEditing: signal(false) }
    ]);

    fixture.detectChanges();
  });

  it("creates and renders the self-service template", () => {
    expect(component).toBeInstanceOf(TokenDetailsComponent);
    expect(fixture.nativeElement.textContent).toContain("Mock serial");
  });
});
