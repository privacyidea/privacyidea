import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenTabComponent } from './token-tab.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';
import { TokenService } from '../../../../services/token/token.service';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { VersionService } from '../../../../services/version/version.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { of, throwError } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { ConfirmationDialogComponent } from '../../confirmation-dialog/confirmation-dialog.component';

describe('TokenTabComponent', () => {
  let component: TokenTabComponent;
  let fixture: ComponentFixture<TokenTabComponent>;
  let tokenServiceSpy: jasmine.SpyObj<TokenService>;
  let matDialogSpy: jasmine.SpyObj<MatDialog>;
  let versionServiceSpy: jasmine.SpyObj<VersionService>;
  let notificationSpy: jasmine.SpyObj<NotificationService>;

  beforeEach(async () => {
    tokenServiceSpy = jasmine.createSpyObj('TokenService', [
      'toggleActive',
      'revokeToken',
      'deleteToken',
      'getTokenDetails',
    ]);
    tokenServiceSpy.toggleActive.and.returnValue(of(null));
    tokenServiceSpy.revokeToken.and.returnValue(of(Object));
    tokenServiceSpy.deleteToken.and.returnValue(of(Object));
    tokenServiceSpy.getTokenDetails.and.returnValue(
      of({
        tokenSerial: 'Mock serial',
        tokenIsSelected: true,
      }),
    );

    matDialogSpy = jasmine.createSpyObj('MatDialog', ['open']);

    versionServiceSpy = jasmine.createSpyObj('VersionService', ['getVersion']);
    versionServiceSpy.getVersion.and.returnValue('1.0.0');

    notificationSpy = jasmine.createSpyObj('NotificationService', [
      'openSnackBar',
    ]);

    await TestBed.configureTestingModule({
      imports: [TokenTabComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: MatDialog, useValue: matDialogSpy },
        { provide: VersionService, useValue: versionServiceSpy },
        { provide: NotificationService, useValue: notificationSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenTabComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal<string>('Mock serial');
    component.selectedContent = signal<string>('token_overview');
    component.revoked = signal<boolean>(false);
    component.active = signal<boolean>(true);
    component.refreshTokenDetails = signal<boolean>(false);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should set version on ngOnInit', () => {
    expect(component.version).toBe('1.0.0');
    expect(versionServiceSpy.getVersion).toHaveBeenCalled();
  });

  describe('Navigation methods', () => {
    it('onClickOverview() sets selectedContent and clears tokenSerial', () => {
      component.onClickOverview();
      expect(component.selectedContent()).toBe('token_overview');
      expect(component.tokenSerial()).toBe('');
    });

    it('onClickEnrollment() sets selectedContent and clears tokenSerial', () => {
      component.onClickEnrollment();
      expect(component.selectedContent()).toBe('token_enrollment');
      expect(component.tokenSerial()).toBe('');
    });

    it('onClickGetSerial() sets selectedContent and clears tokenSerial', () => {
      component.onClickGetSerial();
      expect(component.selectedContent()).toBe('token_get_serial');
      expect(component.tokenSerial()).toBe('');
    });
  });

  describe('toggleActive()', () => {
    it('calls tokenService.toggleActive and refreshes token details on success', () => {
      const refreshSpy = spyOn(component.refreshTokenDetails, 'set');

      component.toggleActive();

      expect(tokenServiceSpy.toggleActive).toHaveBeenCalledWith(
        'Mock serial',
        true,
      );
      expect(tokenServiceSpy.getTokenDetails).toHaveBeenCalledWith(
        'Mock serial',
      );
      expect(refreshSpy).toHaveBeenCalledWith(true);
      expect(notificationSpy.openSnackBar).not.toHaveBeenCalled();
    });

    it('opens a snackBar on error', () => {
      tokenServiceSpy.toggleActive.and.returnValue(
        throwError(() => new Error('Toggle error')),
      );

      component.toggleActive();

      expect(notificationSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to toggle active.',
      );
    });
  });

  describe('revokeToken()', () => {
    it('calls tokenService.revokeToken and refreshes token details on success', () => {
      matDialogSpy.open.and.returnValue({
        afterClosed: () => of(true),
      } as MatDialogRef<ConfirmationDialogComponent>);

      const refreshSpy = spyOn(component.refreshTokenDetails, 'set');

      component.revokeToken();

      expect(tokenServiceSpy.revokeToken).toHaveBeenCalledWith('Mock serial');
      expect(tokenServiceSpy.getTokenDetails).toHaveBeenCalledWith(
        'Mock serial',
      );
      expect(refreshSpy).toHaveBeenCalledWith(true);
    });

    it('opens a snackBar on error', () => {
      matDialogSpy.open.and.returnValue({
        afterClosed: () => of(true),
      } as MatDialogRef<ConfirmationDialogComponent>);

      tokenServiceSpy.revokeToken.and.returnValue(
        throwError(() => new Error('Revoke error')),
      );

      component.revokeToken();

      expect(notificationSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to revoke token.',
      );
    });
  });

  describe('deleteToken()', () => {
    it('calls tokenService.deleteToken and clears tokenSerial and redirects to overview', () => {
      matDialogSpy.open.and.returnValue({
        afterClosed: () => of(true),
      } as MatDialogRef<ConfirmationDialogComponent>);

      component.deleteToken();

      expect(tokenServiceSpy.deleteToken).toHaveBeenCalledWith('Mock serial');
      expect(component.tokenSerial()).toBe('');
      expect(component.selectedContent()).toBe('token_overview');
    });

    it('opens a snackBar on error', () => {
      matDialogSpy.open.and.returnValue({
        afterClosed: () => of(true),
      } as MatDialogRef<ConfirmationDialogComponent>);

      tokenServiceSpy.deleteToken.and.returnValue(
        throwError(() => new Error('Delete error')),
      );

      component.deleteToken();

      expect(notificationSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to delete token.',
      );
    });
  });

  describe('openLostTokenDialog()', () => {
    it('should open a LostToken dialog with the correct data', () => {
      component.openLostTokenDialog();
      expect(matDialogSpy.open).toHaveBeenCalled();

      const dialogCall = matDialogSpy.open.calls.mostRecent();
      const config = dialogCall.args[1] as {
        data: {
          tokenSerial: () => string;
          isLost: () => boolean;
        };
      };

      expect(config.data.tokenSerial()).toBe('Mock serial');
      expect(config.data.isLost()).toBe(false);
    });
  });

  describe('openTheDocs()', () => {
    it('should open the docs link in a new tab', () => {
      const openSpy = spyOn(window, 'open');
      component.openTheDocs();

      expect(openSpy).toHaveBeenCalledWith(
        jasmine.stringMatching(/readthedocs.*1.0.0.*tokens/),
        '_blank',
      );
    });
  });

  describe('when selectedContent = "token_details"', () => {
    beforeEach(() => {
      component.selectedContent.set('token_details');
      fixture.detectChanges();
    });

    it('should show the Token Details button as active', () => {
      const tokenDetailsBtn = fixture.debugElement.query(
        By.css('button.card-button-active'),
      )?.nativeElement;

      expect(tokenDetailsBtn).toBeTruthy();
      expect(tokenDetailsBtn.textContent).toContain('Token Details');
      expect(tokenDetailsBtn.classList).toContain('card-button-active');
    });
  });

  describe('when selectedContent = "token_overview"', () => {
    beforeEach(() => {
      component.selectedContent.set('token_overview');
      fixture.detectChanges();
    });

    it('should show the Overview button as active', () => {
      const overviewBtn = fixture.debugElement.query(
        By.css('button.card-button-active'),
      )?.nativeElement;

      expect(overviewBtn).toBeTruthy();
      expect(overviewBtn.textContent).toContain('Overview');
      expect(overviewBtn.classList).toContain('card-button-active');
    });

    it('should not render the token_details block', () => {
      const tokenDetailsBtn = fixture.debugElement.query(
        By.css(
          'button.card-button-active mat-icon[textContent="health_and_safety"]',
        ),
      );
      expect(tokenDetailsBtn).toBeNull();
    });
  });
});
