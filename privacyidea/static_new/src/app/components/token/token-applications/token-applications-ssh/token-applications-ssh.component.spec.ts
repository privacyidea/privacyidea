/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTableDataSource } from "@angular/material/table";
import { MatTabsModule } from "@angular/material/tabs";
import {
  MockLocalService,
  MockMachineService,
  MockNotificationService,
} from "../../../../../testing/mock-services";
import { MachineService, TokenApplication } from "../../../../services/machine/machine.service";
import { TokenService } from "../../../../services/token/token.service";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { KeywordFilterComponent } from "../../../shared/keyword-filter/keyword-filter.component";
import { TokenApplicationsSshComponent } from "./token-applications-ssh.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("TokenApplicationsSshComponent (Jest)", () => {
  let fixture: ComponentFixture<TokenApplicationsSshComponent>;
  let component: TokenApplicationsSshComponent;

  let mockTokenService: Partial<TokenService> = {};
  let mockKeywordFilterComponent: Partial<KeywordFilterComponent> = {};
  let machineServiceMock: MockMachineService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsSshComponent,
        MatTabsModule,
        KeywordFilterComponent,
        CopyButtonComponent
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineService, useClass: MockMachineService },
        { provide: TokenService, useValue: mockTokenService },
        {
          provide: KeywordFilterComponent,
          useValue: mockKeywordFilterComponent
        },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsSshComponent);
    component = fixture.componentInstance;
    machineServiceMock = TestBed.inject(MachineService) as any;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have correct displayedColumns", () => {
    expect(component.displayedColumns).toEqual([
      "serial",
      "service_id",
      "user"
    ]);
  });

  it("should return object strings correctly", () => {
    const options = { key1: "value1", key2: "value2" };
    expect(component.getObjectStrings(options)).toEqual([
      "key1: value1",
      "key2: value2"
    ]);
  });

  describe("dataSource computed", () => {
    it("returns a MatTableDataSource when tokenApplications() yields data", () => {
      const fakeApps: TokenApplication[] = [
        {
          id: 1,
          machine_id: "m1",
          options: {},
          resolver: "",
          serial: "",
          type: "",
          application: ""
        }
      ];
      machineServiceMock.tokenApplications!.set(fakeApps);

      // trigger recompute
      fixture.detectChanges();

      const ds = component.dataSource();
      expect(ds).toBeInstanceOf(MatTableDataSource);
      expect((ds as MatTableDataSource<TokenApplication>).data).toEqual(
        fakeApps
      );
      expect(component.length()).toBe(1);
    });
  });
});
