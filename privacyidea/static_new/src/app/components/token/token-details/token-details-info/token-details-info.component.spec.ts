import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenDetailsInfoComponent} from './token-details-info.component';
import {TokenService} from '../../../../services/token/token.service';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {of, throwError} from 'rxjs';
import {computed, signal} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {By} from '@angular/platform-browser';

class MockTokenService {
  setTokenInfos() {
    return of(null);
  }

  deleteInfo() {
    return of(null);
  }
}

describe('TokenDetailsInfoComponent', () => {
  let component: TokenDetailsInfoComponent;
  let fixture: ComponentFixture<TokenDetailsInfoComponent>;
  let tokenService: TokenService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsInfoComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {provide: TokenService, useClass: MockTokenService},
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsInfoComponent);
    tokenService = TestBed.inject(TokenService);
    component = fixture.componentInstance;
    component.token_serial = signal('Mock serial');
    component.isEditingInfo = signal(false);
    component.isEditingUser = signal(false);
    component.isAnyEditingOrRevoked = computed(() => {
      return (component.isEditingInfo());
    });
    component.refreshDetails = signal(false);
    component.newInfo = signal({key: '', value: ''});
    component.infoData = signal([{
      keyMap: {key: 'info', label: 'Info'},
      value: {key1: 'value1', key2: 'value2'},
      isEditing: signal(false),
    }]);
    component.detailData = signal([{
      keyMap: {key: 'container_serial', label: 'Container'},
      value: 'container1',
      isEditing: signal(false)
    }]);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should dynamically render and toggle editing state', () => {
    component.isEditingInfo.set(false);
    fixture.detectChanges();

    let nonEditingItems = fixture.nativeElement.querySelectorAll('.info-row');
    expect(nonEditingItems.length).toBeGreaterThan(0);
    nonEditingItems.forEach((item: any) => {
      expect(item.querySelector('.info-span-title')).toBeTruthy();
      expect(item.querySelector('.info-span-value')).toBeTruthy();
    });

    component.isEditingInfo.set(true);
    fixture.detectChanges();

    let editingItems = fixture.nativeElement.querySelectorAll('.flex-row');
    expect(editingItems.length).toBeGreaterThan(0);
    editingItems.forEach((item: any) => {
      expect(item.querySelector('mat-label')).toBeTruthy();
      expect(item.querySelector('textarea.info-input')).toBeTruthy();
    });

    const newKeyInput = fixture.nativeElement.querySelector('input[placeholder="Add new key"]');
    const newValueTextarea = fixture.nativeElement.querySelector('textarea[placeholder="Add new info"]');

    expect(newKeyInput).toBeTruthy();
    expect(newValueTextarea).toBeTruthy();
  });

  it('should set token infos', () => {
    spyOn(tokenService, 'setTokenInfos').and.callThrough();
    component.saveInfo({});
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith('Mock serial', jasmine.any(Object));
  });

  it('should handle edit and save for information details', () => {
    spyOn(tokenService, 'setTokenInfos').and.callThrough();
    spyOn(component, 'saveInfo').and.callThrough();

    component.isEditingInfo.set(true);
    fixture.detectChanges();
    expect(component.isAnyEditingOrRevoked()).toBeTruthy();

    component.newInfo.set({key: 'newKey', value: 'newValue'});
    fixture.detectChanges();

    const editButtonsComponent = fixture.debugElement.query(By.css('app-edit-buttons'));
    expect(editButtonsComponent).toBeTruthy();

    const saveButton = editButtonsComponent.nativeElement.querySelector('.edit-button-container' +
      ' .black:nth-child(1)');
    expect(saveButton).toBeTruthy();

    saveButton.click();
    fixture.detectChanges();

    expect(component.saveInfo).toHaveBeenCalled();

    const newInfo = component.infoData().find(info => info.keyMap.key === 'info')?.value;
    expect(newInfo).toEqual(jasmine.objectContaining({newKey: 'newValue'}));
  });

  it('should delete info', () => {
    spyOn(tokenService, 'deleteInfo').and.callThrough();
    component.deleteInfo('infoKey');
    expect(tokenService.deleteInfo).toHaveBeenCalledWith('Mock serial', 'infoKey');
  });

  it('should handle error when deleting info fails', () => {
    spyOn(tokenService, 'deleteInfo').and.returnValue(throwError(() => new Error('Deletion failed')));
    spyOn(console, 'error');
    component.deleteInfo('infoKey');
    expect(console.error).toHaveBeenCalledWith('Failed to delete info', jasmine.any(Error));
  });

});
