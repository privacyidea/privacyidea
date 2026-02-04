import { TestBed } from "@angular/core/testing";
import { WelcomeDialogService } from "./welcome-dialog.service";
import { MatDialog } from "@angular/material/dialog";
import { AuthService } from "../auth/auth.service";
import { signal } from "@angular/core";

describe("WelcomeDialogService", () => {
  let dialogMock: { open: jest.Mock };
  let authMock: Pick<InstanceType<typeof AuthService>, "isAuthenticated" | "hideWelcome" | "subscriptionStatus">;

  beforeEach(() => {
    dialogMock = { open: jest.fn() };
    authMock = {
      isAuthenticated: signal(false) as any,
      hideWelcome: signal(false) as any,
      subscriptionStatus: signal(0) as any
    } as any;

    TestBed.configureTestingModule({
      providers: [
        WelcomeDialogService,
        { provide: MatDialog, useValue: dialogMock },
        { provide: AuthService, useValue: authMock }
      ]
    });
  });

  it("opens dialog when authenticated and not explicitly hidden by status===3", () => {
    (authMock.isAuthenticated as any).set(true);
    (authMock.hideWelcome as any).set(false);
    (authMock.subscriptionStatus as any).set(2);
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.flushEffects();

    expect(service.opened()).toBe(true);
  });

  it("does NOT open when hideWelcome is true and subscriptionStatus===3", () => {
    (authMock.isAuthenticated as any).set(true);
    (authMock.hideWelcome as any).set(true);
    (authMock.subscriptionStatus as any).set(3);
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.flushEffects();

    expect(service.opened()).toBe(false);
  });

  it("does NOT open when not authenticated", () => {
    (authMock.isAuthenticated as any).set(false);
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.flushEffects();

    expect(service.opened()).toBe(false);
  });
});
