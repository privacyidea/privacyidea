import { TestBed } from "@angular/core/testing";
import { Subject } from "rxjs";
import { MatDialog } from "@angular/material/dialog";
import { DialogService } from "./dialog.service";
import { AuthService } from "../auth/auth.service";
import { MockAuthService, MockLocalService, MockNotificationService } from "../../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

jest.mock(
  "../../components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component",
  () => ({
    TokenEnrollmentFirstStepDialogComponent: class TokenEnrollmentFirstStepDialogComponent {
    }
  })
);
jest.mock(
  "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component",
  () => ({
    TokenEnrollmentLastStepDialogComponent: class TokenEnrollmentLastStepDialogComponent {
    }
  })
);
jest.mock(
  "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component",
  () => ({
    TokenEnrollmentLastStepDialogSelfServiceComponent: class TokenEnrollmentLastStepDialogSelfServiceComponent {
    }
  })
);
jest.mock("../../components/shared/confirmation-dialog/confirmation-dialog.component", () => ({
  ConfirmationDialogComponent: class ConfirmationDialogComponent {
  }
}));

const matDialogStub = {
  openDialogs: [] as any[],
  open: jest.fn((_c: any, _cfg: any) => {
    const subj = new Subject<any>();
    const ref: any = {
      afterClosed: () => subj.asObservable(),
      close: (v?: any) => {
        subj.next(v);
        subj.complete();
        matDialogStub.openDialogs = matDialogStub.openDialogs.filter((r) => r !== ref);
      }
    };
    matDialogStub.openDialogs.push(ref);
    return ref;
  })
};

describe("DialogService", () => {
  let dialogService: DialogService;
  let authService: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    matDialogStub.openDialogs.length = 0;
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialog, useValue: matDialogStub },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    });
    dialogService = TestBed.inject(DialogService);
    authService = TestBed.inject(AuthService) as any;
  });

  it("openTokenEnrollmentFirstStepDialog handles multiple opens", () => {
    const cfg = { data: { enrollmentResponse: {} } } as any;
    const first = dialogService.openTokenEnrollmentFirstStepDialog(cfg);
    expect(dialogService.isTokenEnrollmentFirstStepDialogOpen).toBe(true);
    const second = dialogService.openTokenEnrollmentFirstStepDialog(cfg);
    expect(first).not.toBe(second);
    expect(matDialogStub.openDialogs.length).toBe(1);
    second.close();
    expect(dialogService.isTokenEnrollmentFirstStepDialogOpen).toBe(false);
  });

  it("openTokenEnrollmentLastStepDialog picks admin component", async () => {
    await dialogService.openTokenEnrollmentLastStepDialog({ data: {} } as any);
    const componentName = matDialogStub.open.mock.calls.at(-1)?.[0].name ?? "none";
    expect(componentName).toBe("TokenEnrollmentLastStepDialogComponent");
  });

  it("openTokenEnrollmentLastStepDialog picks self‑service component", async () => {
    authService.role.set("user");
    await dialogService.openTokenEnrollmentLastStepDialog({ data: {} } as any);
    const componentName = matDialogStub.open.mock.calls.at(-1)?.[0].name ?? "none";
    expect(componentName).toBe("TokenEnrollmentLastStepDialogSelfServiceComponent");
  });

  it("closeTokenEnrollmentLastStepDialog closes ref", async () => {
    await dialogService.openTokenEnrollmentLastStepDialog({ data: {} } as any);
    expect(matDialogStub.openDialogs.length).toBe(1);
    dialogService.closeTokenEnrollmentLastStepDialog();
    expect(matDialogStub.openDialogs.length).toBe(0);
  });

  it("confirm resolves true and false", async () => {
    const pTrue = dialogService.confirm({ data: {} } as any);
    matDialogStub.openDialogs.at(-1)?.close(true);
    await expect(pTrue).resolves.toBe(true);

    const pFalse = dialogService.confirm({ data: {} } as any);
    matDialogStub.openDialogs.at(-1)?.close(null);
    await expect(pFalse).resolves.toBe(false);
  });

  it("isAnyDialogOpen reflects state", () => {
    expect(dialogService.isAnyDialogOpen()).toBe(false);
    dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse: {} }
    } as any);
    expect(dialogService.isAnyDialogOpen()).toBe(true);
  });

  it("closeTokenEnrollmentFirstStepDialog calls close on the ref", () => {
    const ref = dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse: {} }
    } as any);

    const closeSpy = jest.spyOn(ref, "close");
    dialogService.closeTokenEnrollmentFirstStepDialog();

    expect(closeSpy).toHaveBeenCalled();
    expect(dialogService.isTokenEnrollmentFirstStepDialogOpen).toBe(false);
  });
});
