import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenTabComponent } from './token-tab.component';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import {
  BrowserAnimationsModule,
  provideNoopAnimations,
} from '@angular/platform-browser/animations';

import { signal } from '@angular/core';
import { of } from 'rxjs';
import { By } from '@angular/platform-browser';

import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { TokenService } from '../../../../services/token/token.service';
import { VersionService } from '../../../../services/version/version.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { ContentService } from '../../../../services/content/content.service';

import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { TokenSelectedContentKey } from '../../token.component';

describe('TokenTabComponent', () => {
  let component: TokenTabComponent;
  let fixture: ComponentFixture<TokenTabComponent>;

  const tokenServiceStub = {
    tokenIsActive: signal<boolean>(true),
    tokenIsRevoked: signal<boolean>(false),
    tokenSerial: signal<string>('Mock serial'),
    tokenSelection: signal<any[]>([]),

    toggleActive: jest.fn().mockReturnValue(of(null)),
    revokeToken: jest.fn().mockReturnValue(of(null)),
    deleteToken: jest.fn().mockReturnValue(of(null)),
    getTokenDetails: jest.fn().mockReturnValue(of({})),

    tokenDetailResource: { reload: jest.fn() },
    tokenResource: { reload: jest.fn() },
  } as unknown as TokenService;

  const matDialogRefStub = {
    afterClosed: () => of(true),
  } as unknown as MatDialogRef<ConfirmationDialogComponent>;

  const matDialogStub = {
    open: jest.fn().mockReturnValue(matDialogRefStub),
  } as unknown as MatDialog;

  const versionServiceStub = {
    getVersion: jest.fn().mockReturnValue('1.0.0'),
  } as unknown as VersionService;

  const notificationServiceStub = {
    openSnackBar: jest.fn(),
  } as unknown as NotificationService;

  const contentServiceStub = {
    selectedContent: signal<TokenSelectedContentKey>('token_overview'),
  } as unknown as ContentService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenTabComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        { provide: TokenService, useValue: tokenServiceStub },
        { provide: MatDialog, useValue: matDialogStub },
        { provide: VersionService, useValue: versionServiceStub },
        { provide: NotificationService, useValue: notificationServiceStub },
        { provide: ContentService, useValue: contentServiceStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('sets the version on ngOnInit', () => {
    expect(component.version).toBe('1.0.0');
    expect(versionServiceStub.getVersion).toHaveBeenCalled();
  });

  describe('toggleActive()', () => {
    it('calls service, reloads details', () => {
      component.toggleActive();

      expect(tokenServiceStub.toggleActive).toHaveBeenCalledWith(
        'Mock serial',
        true,
      );
      expect(tokenServiceStub.getTokenDetails).toHaveBeenCalledWith(
        'Mock serial',
      );
      expect(tokenServiceStub.tokenDetailResource.reload).toHaveBeenCalled();
      expect(notificationServiceStub.openSnackBar).not.toHaveBeenCalled();
    });
  });

  describe('revokeToken()', () => {
    it('opens confirm dialog, revokes, reloads details', () => {
      component.revokeToken();

      expect(matDialogStub.open).toHaveBeenCalled();
      expect(tokenServiceStub.revokeToken).toHaveBeenCalledWith('Mock serial');
      expect(tokenServiceStub.getTokenDetails).toHaveBeenCalledWith(
        'Mock serial',
      );
      expect(tokenServiceStub.tokenDetailResource.reload).toHaveBeenCalled();
    });
  });

  describe('deleteToken()', () => {
    it('opens confirm dialog, deletes, clears serial, returns to overview', () => {
      component.deleteToken();

      expect(matDialogStub.open).toHaveBeenCalled();
      expect(tokenServiceStub.deleteToken).toHaveBeenCalledWith('Mock serial');
      expect(tokenServiceStub.tokenSerial()).toBe('');
      expect(contentServiceStub.selectedContent()).toBe('token_overview');
    });
  });

  describe('openLostTokenDialog()', () => {
    it('passes the isLost & tokenSerial signals to the dialog', () => {
      component.openLostTokenDialog();

      expect(matDialogStub.open).toHaveBeenCalledWith(expect.any(Function), {
        data: {
          isLost: component.isLost,
          tokenSerial: component.tokenSerial,
        },
      });
    });
  });

  describe('template bindings', () => {
    it('highlights “Token Details” when selectedContent = token_details', () => {
      contentServiceStub.selectedContent.set('token_details');
      fixture.detectChanges();

      const btn = fixture.debugElement.query(
        By.css('button.card-button-active'),
      )?.nativeElement;

      expect(btn).toBeTruthy();
      expect(btn.textContent).toContain('Token Details');
    });

    it('highlights “Overview” when selectedContent = token_overview', () => {
      contentServiceStub.selectedContent.set('token_overview');
      fixture.detectChanges();

      const btn = fixture.debugElement.query(
        By.css('button.card-button-active'),
      )?.nativeElement;

      expect(btn).toBeTruthy();
      expect(btn.textContent).toContain('Overview');

      const icon = fixture.debugElement.query(
        By.css(
          'button.card-button-active mat-icon[textContent="health_and_safety"]',
        ),
      );
      expect(icon).toBeNull();
    });
  });
});
